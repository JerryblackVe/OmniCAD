# -*- coding: utf-8 -*-
"""Insertar derivación: vínculo externo, parámetros, bocetos, API y diálogo."""
import copy

import pytest

from omnicad import api
from omnicad.io_archivos import proyecto
from omnicad.nucleo import geometria as geo
from omnicad.restricciones import Boceto
from omnicad.timeline import entidades
from omnicad.timeline.documento import Documento, ErrorDocumento
from omnicad.timeline.operaciones import ErrorOperacion, OpBoceto, OpExtrusion, OpPrimitiva
from omnicad.timeline.ops_derivacion import OpDerivacion


@pytest.fixture
def origen(tmp_path):
    doc = Documento()
    doc.parametros.agregar("ancho", "10 mm")
    doc.agregar(OpPrimitiva(doc.nuevo_id(), "Caja", ancho="ancho", largo="4", alto="3"))
    doc.agregar(OpPrimitiva(doc.nuevo_id(), "Otra caja", ancho="2", largo="2", alto="2", x="50"))
    boceto = Boceto()
    boceto.agregar_rectangulo((0, 0), (4, 3))
    doc.agregar(OpBoceto(doc.nuevo_id(), "Rectángulo", boceto=boceto))
    ruta = tmp_path / "origen.omnicad"
    proyecto.guardar(doc, ruta)
    return doc, ruta


def _volumen(doc, cid, esperado):
    forma = doc.estado_final.cuerpos[cid].forma
    assert geo.es_valida(forma)
    assert geo.volumen(forma) == pytest.approx(esperado)


def _ok(respuesta):
    assert respuesta["ok"], respuesta
    return respuesta["result"]


def test_derivar_un_cuerpo_y_parametro_actualizar_y_borrar_origen(origen):
    fuente, ruta = origen
    doc = Documento()
    op = OpDerivacion(doc.nuevo_id(), archivo=str(ruta), cuerpos=["op1.c1"], parametros=["ancho"])
    receta = copy.deepcopy(op.p)
    assert doc.agregar(op).estado == "ok"
    assert len(doc.estado_final.cuerpos) == 1
    _volumen(doc, "op1.c1", geo.volumen(fuente.estado_final.cuerpos["op1.c1"].forma))
    assert doc.parametros.valores()["ancho"] == 10
    doc.agregar(OpPrimitiva(doc.nuevo_id(), ancho="ancho", largo="2", alto="1", x="100"))
    fuente.parametros.modificar("ancho", "20 mm")
    fuente.recalcular()
    proyecto.guardar(fuente, ruta)
    doc.recalcular()
    _volumen(doc, "op1.c1", 240)
    _volumen(doc, "op2.c1", 40)
    assert doc.parametros.valores()["ancho"] == 20
    assert op.p == receta
    ruta.unlink()
    doc.recalcular()
    resultado = doc.resultado(op.id)
    assert resultado.estado == "error"
    assert "proyecto de origen" in resultado.mensaje and str(ruta) in resultado.mensaje
    assert "No encuentro" in resultado.mensaje


def test_parametro_resuelto_sin_importar_sus_dependencias_y_recalculo_parcial(origen):
    fuente, ruta = origen
    fuente.parametros.agregar("doble", "ancho * 2")
    proyecto.guardar(fuente, ruta)
    doc = Documento()
    assert doc.agregar(OpDerivacion(doc.nuevo_id(), archivo=str(ruta), parametros=["doble"])).estado == "ok"
    assert doc.parametros.valores() == {"doble": 20}
    doc.parametros.agregar("triple", "doble * 3")
    doc.agregar(OpPrimitiva(doc.nuevo_id(), ancho="triple", largo="1", alto="1"))
    fuente.parametros.modificar("ancho", "15 mm")
    fuente.recalcular()
    proyecto.guardar(fuente, ruta)
    doc.recalcular()
    assert doc.parametros.valores() == {"doble": 30, "triple": 90}
    doc.agregar(OpPrimitiva(doc.nuevo_id(), ancho="doble", largo="1", alto="1", x="100"))
    _volumen(doc, "op2.c1", 90)
    _volumen(doc, "op3.c1", 30)


def test_boceto_derivado_utilizable_y_dependiente(origen):
    fuente, ruta = origen
    doc = Documento()
    assert doc.agregar(OpDerivacion(doc.nuevo_id(), archivo=str(ruta), bocetos=["Rectángulo"])).estado == "ok"
    bid = "op1.op3"
    br = doc.estado_final.bocetos[bid]
    assert br.op_id == bid and br.nombre == "Rectángulo"
    assert entidades.dependencias({"tipo": "boceto", "boceto": bid}) == {"op1"}
    op = OpExtrusion(doc.nuevo_id(), boceto=bid,
                     perfiles=[OpExtrusion.referencia_perfil(br.perfiles[0])], distancia="5")
    assert doc.agregar(op).estado == "ok"
    _volumen(doc, "op2.c1", 60)
    assert not doc.puede_mover("op1", 1)[0]
    with pytest.raises(ErrorDocumento, match="usan"):
        doc.eliminar("op1")
    boceto = Boceto()
    boceto.agregar_rectangulo((0, 0), (8, 3))
    fuente.reemplazar("op3", OpBoceto("op3", "Rectángulo", boceto=boceto))
    proyecto.guardar(fuente, ruta)
    doc.recalcular()
    _volumen(doc, "op2.c1", 120)


def test_guardar_abrir_ignora_cache_local_del_vinculo_y_sus_dependientes(origen, tmp_path):
    fuente, ruta = origen
    doc = Documento()
    doc.agregar(OpDerivacion(doc.nuevo_id(), archivo=str(ruta), cuerpos=["op1.c1"], parametros=["ancho"]))
    doc.agregar(OpPrimitiva(doc.nuevo_id(), ancho="ancho", largo="1", alto="1", x="100"))
    doc._duraciones = [1, 1]  # Fuerza la caché que normalmente solo guardan los pasos lentos.
    destino = proyecto.guardar(doc, tmp_path / "destino.omnicad")
    fuente.parametros.modificar("ancho", "25 mm")
    fuente.recalcular()
    proyecto.guardar(fuente, ruta)
    abierto = proyecto.abrir(destino)
    _volumen(abierto, "op1.c1", 300)
    _volumen(abierto, "op2.c1", 25)
    assert abierto.parametros.valores()["ancho"] == 25
    assert abierto.operaciones[0].p["archivo"] == str(ruta)


def test_api_insert_derive_y_un_solo_deshacer(origen):
    _, ruta = origen
    sesion = api.Sesion()
    resultado = _ok(api.llamar(sesion, "insert_derive", {
        "source_path": str(ruta), "bodies": ["op1.c1"], "sketches": ["op3"],
        "parameters": ["ancho"], "name": "Vínculo"}))
    assert resultado["type"] == "derivacion" and resultado["status"] == "ok"
    assert resultado["name"] == "Vínculo" and resultado["new_bodies"] == ["op1.c1"]
    assert resultado["parameters"] == ["ancho"]
    _volumen(sesion.doc, "op1.c1", 120)
    assert sesion.doc.parametros.valores()["ancho"] == 10
    assert "op1.op3" in sesion.doc.estado_final.bocetos
    _ok(api.llamar(sesion, "undo"))
    assert not sesion.doc.operaciones and not len(sesion.doc.parametros)
    _ok(api.llamar(sesion, "redo"))
    _volumen(sesion.doc, "op1.c1", 120)


def test_run_operation_con_ids_del_origen_y_opciones_para_agentes(origen):
    _, ruta = origen
    sesion = api.Sesion()
    resultado = _ok(api.llamar(sesion, "run_operation", {"type": "derivacion", "params": {
        "archivo": str(ruta), "cuerpos": ["op2.c1"], "parametros": ["ancho"]}}))
    assert resultado["status"] == "ok"
    _volumen(sesion.doc, "op1.c1", 8)
    descripcion = _ok(api.llamar(sesion, "describe_operation", {"type": "derivacion"}))
    assert {p["name"] for p in descripcion["params"]} == set(OpDerivacion.PARAMS)


@pytest.mark.parametrize("seleccion", [{}, {"bodies": ["inexistente"]}, {"sketches": ["inexistente"]},
                                       {"parameters": ["inexistente"]}])
def test_api_rechaza_seleccion_invalida_sin_tocar_documento(origen, seleccion):
    _, ruta = origen
    sesion = api.Sesion()
    antes = sesion.doc.a_dict()
    resultado = api.llamar(sesion, "insert_derive", {"source_path": str(ruta), **seleccion})
    assert not resultado["ok"]
    assert sesion.doc.a_dict() == antes


def test_api_no_sobrescribe_parametro_local(origen):
    _, ruta = origen
    sesion = api.Sesion()
    sesion.doc.parametros.agregar("ancho", "99 mm")
    antes = sesion.doc.a_dict()
    resultado = api.llamar(sesion, "insert_derive", {"source_path": str(ruta), "parameters": ["ancho"]})
    assert not resultado["ok"] and "ya existe" in resultado["mensaje"]
    assert sesion.doc.a_dict() == antes


def test_previa_valida_parametros_sin_modificar_el_documento(origen):
    _, ruta = origen
    doc = Documento()
    op = OpDerivacion(doc.nuevo_id(), archivo=str(ruta), cuerpos=["op1.c1"], parametros=["ancho"])
    antes = doc.a_dict()
    estado, avisos = doc.previsualizar(op)
    assert len(estado.cuerpos) == 1 and not avisos
    assert doc.a_dict() == antes
    doc.parametros.agregar("ancho", "99 mm")
    antes = doc.a_dict()
    with pytest.raises(ErrorOperacion, match="ya existe"):
        doc.previsualizar(op)
    assert doc.a_dict() == antes


def test_api_archivo_faltante_y_lector_seguro(origen, monkeypatch):
    _, ruta = origen
    sesion = api.Sesion()
    resultado = api.llamar(sesion, "insert_derive", {"source_path": str(ruta.with_name("no.omnicad")),
                                                  "bodies": ["op1.c1"]})
    assert not resultado["ok"] and resultado["error_kind"] == "FILE_NOT_FOUND"
    monkeypatch.setattr(proyecto, "TOPE_MIEMBRO_ZIP", 10)
    resultado = api.llamar(sesion, "insert_derive", {"source_path": str(ruta), "bodies": ["op1.c1"]})
    assert not resultado["ok"] and "tope" in resultado["mensaje"]
    doc = Documento()
    resultado = doc.agregar(OpDerivacion(doc.nuevo_id(), archivo=str(ruta), cuerpos=["op1.c1"]))
    assert resultado.estado == "error" and "tope" in resultado.mensaje


def test_origen_circular_da_error_claro(tmp_path):
    ruta = tmp_path / "circular.omnicad"
    doc = Documento()
    doc.agregar(OpDerivacion(doc.nuevo_id(), archivo=str(ruta), cuerpos=["op1.c1"]))
    proyecto.guardar(doc, ruta)
    doc.recalcular()
    assert doc.resultados[0].estado == "error" and "circular" in doc.resultados[0].mensaje


def test_seleccion_desaparecida_avisa(origen):
    _, ruta = origen
    doc = Documento()
    resultado = doc.agregar(OpDerivacion(doc.nuevo_id(), archivo=str(ruta), cuerpos=["no existe"],
                                        bocetos=["no existe"], parametros=["no_existe"]))
    assert resultado.estado == "aviso" and "ya no está" in resultado.mensaje
    assert not doc.estado_final.cuerpos and not doc.estado_final.bocetos


def test_dialogo_seleccion_edicion_previa_y_cinta(origen, monkeypatch):
    from PySide6.QtCore import Qt
    from PySide6.QtWidgets import QApplication, QFileDialog

    from omnicad.ui.cinta import INSERTAR
    from omnicad.ui.comando import ContextoComando, PanelComando
    from omnicad.ui.comandos import CATALOGO, POR_TIPO
    from omnicad.ui.comandos.derivacion import InsertarDerivacion
    from omnicad.ui.visor3d import Visor3D

    app = QApplication.instance() or QApplication([])
    _, ruta = origen
    doc, visor = Documento(), Visor3D()
    cmd = InsertarDerivacion()
    panel = PanelComando(cmd, ContextoComando(doc), visor)
    monkeypatch.setattr(QFileDialog, "getOpenFileName", lambda *a: (str(ruta), ""))
    panel.widgets["examinar"].click()
    assert panel.widgets["cuerpos"].count() == 2
    assert panel.widgets["bocetos"].count() == 1
    panel.widgets["cuerpos"].item(0).setCheckState(Qt.Checked)
    panel.widgets["parametros"].item(0).setCheckState(Qt.Checked)
    panel._calcular_previa()
    assert not len(doc.parametros) and not doc.operaciones
    aceptadas = []
    panel.aceptado.connect(aceptadas.append)
    panel.aceptar()
    assert len(aceptadas) == 1
    op = aceptadas[0]
    assert doc.agregar(op).estado == "ok"
    _volumen(doc, f"{op.id}.c1", 120)
    editor = PanelComando(InsertarDerivacion(), ContextoComando(doc, op=op), visor)
    assert editor.valores["cuerpos"] == ["op1.c1"] and editor.valores["parametros"] == ["ancho"]
    editada = editor.comando.construir(editor.valores, editor.ctx)
    assert editada.id == op.id and editada.p == op.p
    editor.cancelar()
    assert CATALOGO["insertar_derivacion"] is InsertarDerivacion
    assert POR_TIPO["derivacion"] is InsertarDerivacion
    assert any(item[1:3] == ("Insertar derivación", "insertar_derivacion") for item in INSERTAR[2])
    panel.deleteLater()
    editor.deleteLater()
    visor.deleteLater()
    app.processEvents()
