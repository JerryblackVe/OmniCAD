# -*- coding: utf-8 -*-
"""ADMINISTRAR/CONFIGURAR/UTILIDADES: lista de materiales, configuraciones, scripts, operación base y CSV de
parámetros."""
import os

import pytest

from omnicad.nucleo import geometria as g
from omnicad.timeline.documento import Documento
from omnicad.timeline.operaciones import OpOperacionBase, OpPrimitiva


@pytest.fixture(scope="module", autouse=True)
def app_qt():
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    from PySide6.QtWidgets import QApplication
    return QApplication.instance() or QApplication([])


def _doc():
    doc = Documento()
    doc.parametros.agregar("lado", "10 mm")
    doc.agregar(OpPrimitiva(doc.nuevo_id(), forma="caja", ancho="lado", largo="lado", alto="lado"))
    doc.agregar(OpPrimitiva(doc.nuevo_id(), forma="caja", ancho="10", largo="10", alto="10", x="50"))
    doc.agregar(OpPrimitiva(doc.nuevo_id(), forma="cilindro", radio="2", alto="10", x="90"))
    return doc


def test_lista_de_materiales_agrupa_iguales():
    from omnicad.ui.administrar import DialogoListaMateriales, filas_bom
    doc = _doc()
    doc.set_propiedad(["op3.c1"], "material", "Aluminio 6061")
    filas = filas_bom(doc, nombre_de=lambda c: "Pieza" if c.id != "op3.c1" else "Pasador")
    assert sorted((f[1], f[2]) for f in filas) == [("Pasador", 1), ("Pieza", 2)]
    pasador = next(f for f in filas if f[1] == "Pasador")
    assert pasador[4] == pytest.approx(3.14159 * 4 * 10 * 2.70e-3, rel=1e-4)
    csv = DialogoListaMateriales(doc, nombre_de=lambda c: c.nombre).texto_csv()
    assert csv.startswith("N.º,Nombre,Cantidad")


def test_configuraciones_aplican_parametros_y_supresion():
    doc = _doc()
    tabla = {"columnas": [{"tipo": "parametro", "nombre": "lado"}, {"tipo": "suprimir", "op": "op3"}],
             "filas": [{"nombre": "Chica", "valores": ["10 mm", "no"]}, {"nombre": "Grande", "valores": ["20 mm", "sí"]}]}
    doc.aplicar_configuracion(tabla, "Grande")
    assert g.volumen(doc.estado_final.cuerpos["op1.c1"].forma) == pytest.approx(8000)
    assert "op3.c1" not in doc.estado_final.cuerpos
    doc.aplicar_configuracion(doc.configuraciones, "Chica")
    assert g.volumen(doc.estado_final.cuerpos["op1.c1"].forma) == pytest.approx(1000)
    doc.deshacer()
    assert doc.configuraciones["activa"] == "Grande"
    assert Documento.desde_dict(doc.a_dict()).configuraciones["filas"][1]["nombre"] == "Grande"


def test_script_operacion_base_y_csv(tmp_path):
    from omnicad.ui.administrar import ejecutar_script
    from omnicad.ui.dialogos import DialogoParametros

    class _App:
        pass
    app = _App()
    app.doc = _doc()
    ok, salida = ejecutar_script("print(len(doc.estado_final.cuerpos))", app)
    assert ok and salida.strip() == "3"
    ok, salida = ejecutar_script("1/0", app)
    assert not ok and "ZeroDivisionError" in salida
    doc = app.doc
    op = OpOperacionBase.desde_cuerpos(doc.nuevo_id(), [doc.estado_final.cuerpos["op1.c1"]])
    doc.agregar(op)
    assert doc.resultado(op.id).estado == "ok"
    assert g.volumen(doc.estado_final.cuerpos["op1.c1"].forma) == pytest.approx(1000)
    dlg = DialogoParametros(doc.parametros)
    filas = dlg.filas_csv()
    assert filas[0][:3] == ["lado", "mm", "10 mm"]
    ruta = tmp_path / "p.csv"
    ruta.write_text("Name,Unit,Expression,Value,Comments\nlado,mm,25 mm,25,\nalto,mm,lado * 2,50,nuevo\n",
                    encoding="utf-8")
    assert dlg.importar_csv(ruta) == 2
    assert dlg.resultado.valores()["alto"] == pytest.approx(50)
