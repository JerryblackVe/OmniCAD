# -*- coding: utf-8 -*-
"""Regresiones de los errores encontrados por la revisión independiente de la Fase 3."""
import json
import zipfile

import pytest

from omnicad.io_archivos import proyecto
from omnicad.nucleo import geometria as g
from omnicad.nucleo import perfiles as pf
from omnicad.restricciones import Boceto
from omnicad.timeline.documento import Documento, ErrorDocumento
from omnicad.timeline.operaciones import OpBoceto, OpExtrusion, OpPrimitiva
from omnicad.timeline.parametros import ErrorExpresion, TablaParametros, evaluar


def _triangulo():
    """Triángulo con base = parámetro 'a' y los otros lados de 10 mm."""
    b = Boceto()
    A, B, C = b.agregar_punto(0, 0), b.agregar_punto(12, 0), b.agregar_punto(6, 8)
    base = b.agregar_linea(A, B)
    lado1, lado2 = b.agregar_linea(B, C), b.agregar_linea(C, A)
    b.agregar_restriccion("fijo", [A])
    b.agregar_restriccion("horizontal", [base])
    b.agregar_cota("distancia", [base], "a")
    b.agregar_cota("distancia", [lado1], "10")
    b.agregar_cota("distancia", [lado2], "10")
    return b


def test_parametro_imposible_no_rompe_el_boceto_para_siempre():
    doc = Documento()
    doc.parametros.agregar("a", "12 mm")
    doc.agregar(OpBoceto(doc.nuevo_id(), boceto=_triangulo()))
    assert doc.resultados[0].estado == "ok" and len(doc.estado_final.bocetos["op1"].perfiles) == 1
    for valor, esperado in (("30 mm", "aviso"), ("12 mm", "ok")):      # 30 viola la desigualdad triangular
        t = TablaParametros.desde_lista(doc.parametros.a_lista())
        t.modificar("a", valor)
        doc.aplicar_parametros(t)
        assert doc.resultados[0].estado == esperado
    assert len(doc.estado_final.bocetos["op1"].perfiles) == 1


@pytest.mark.parametrize("expr", ["(-8)**0.5", "2**2000", "floor(1e308*10)", "round(1e999)", "10**400", "sqrt(-1)"])
def test_expresiones_que_desbordan_dan_error_controlado(expr):
    with pytest.raises(ErrorExpresion):
        evaluar(expr)


def test_no_se_puede_borrar_ni_renombrar_un_parametro_en_uso():
    doc = Documento()
    doc.parametros.agregar("alto", "8 mm")
    doc.agregar(OpPrimitiva(doc.nuevo_id(), forma="caja", alto="alto"))
    sin_alto = TablaParametros()
    with pytest.raises(ErrorDocumento, match="alto"):
        doc.aplicar_parametros(sin_alto)
    assert "alto" in doc.parametros


def test_corte_automatico_depende_del_cuerpo_que_corta():
    doc = Documento()
    doc.agregar(OpPrimitiva(doc.nuevo_id(), forma="caja"))
    doc.agregar(OpPrimitiva(doc.nuevo_id(), forma="esfera", radio="5", x="20", y="20", z="20", operacion="cortar"))
    assert "op1" in doc.operacion("op2").dependencias()
    ok, _ = doc.puede_mover("op1", 1)
    assert not ok
    with pytest.raises(ErrorDocumento):
        doc.eliminar("op1")


def test_firma_de_arcos_distingue_las_dos_mitades():
    b = Boceto()
    izq, der = b.agregar_punto(-10, 0), b.agregar_punto(10, 0)
    arriba = b.agregar_arco_centro((0, 0), der, izq)      # mitad superior (antihoraria de der a izq)
    abajo = b.agregar_arco_centro((0, 0), izq, der)       # mitad inferior
    diametro = b.agregar_linea(izq, der)
    firmas = {p.firma for p in pf.detectar(b.geometria(), g.Plano())}
    assert firmas == {frozenset({arriba, diametro}), frozenset({abajo, diametro})}


def test_receta_con_operacion_desconocida_da_error_de_proyecto(tmp_path):
    ruta = tmp_path / "raro.omnicad"
    with zipfile.ZipFile(ruta, "w") as z:
        z.writestr("manifiesto.json", json.dumps({"formato": proyecto.FORMATO, "version_formato": 1}))
        z.writestr("receta.json", json.dumps({"operaciones": [{"tipo": "teletransporte", "id": "op1"}]}))
    with pytest.raises(proyecto.ErrorProyecto):
        proyecto.abrir(ruta)


# ---------------------------------------------------------------- interfaz (sin ventana visible)
@pytest.fixture(scope="module")
def app_qt():
    import os
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    from PySide6.QtWidgets import QApplication
    return QApplication.instance() or QApplication([])


def _doc_circulo_partido():
    """Círculo cortado por una línea: dos regiones con la MISMA firma; se extruye solo la de arriba."""
    doc = Documento()
    b = Boceto()
    b.agregar_circulo((0, 0), 10)
    b.agregar_linea((-12, 0), (12, 0))
    doc.agregar(OpBoceto(doc.nuevo_id(), boceto=b))
    perfiles = doc.estado_final.bocetos["op1"].perfiles
    arriba = max(perfiles, key=lambda p: p.centroide_uv[1])
    doc.agregar(OpExtrusion(doc.nuevo_id(), boceto="op1", perfiles=[OpExtrusion.referencia_perfil(arriba)],
                            distancia="10"))
    return doc


# (la regresión «editar extrusión sin cambios» vive ahora en test_comandos.py, con el diálogo nuevo)


def test_un_punto_fijo_no_se_arrastra(app_qt):
    from PySide6.QtCore import Qt
    from PySide6.QtTest import QTest
    from omnicad.ui.editor_boceto import Lienzo
    b = Boceto()
    linea = b.agregar_linea((0, 0), (20, 0))
    fijo = b.curvas[linea].p1
    b.agregar_restriccion("fijo", [fijo])
    lz = Lienzo(b, TablaParametros().evaluar)
    lz.resize(600, 400)
    lz.centro, lz.escala = [10.0, 0.0], 10.0
    origen = lz.a_px(0, 0).toPoint()
    QTest.mousePress(lz, Qt.LeftButton, Qt.NoModifier, origen)
    QTest.mouseMove(lz, lz.a_px(30, 25).toPoint())
    QTest.mouseRelease(lz, Qt.LeftButton, Qt.NoModifier, lz.a_px(30, 25).toPoint())
    assert b.coords(fijo) == (0.0, 0.0)
