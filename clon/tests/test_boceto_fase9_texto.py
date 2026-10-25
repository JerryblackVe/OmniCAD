"""BOC-20: pivotes del marco y parámetros de texto de Fusion."""
import math

import pytest

from omnicad import api
from omnicad.api.herramientas_boceto import boceto_activo, op_boceto
from omnicad.timeline.parametros import ErrorExpresion, TablaParametros


def llamar(sesion, nombre, **argumentos):
    respuesta = api.llamar(sesion, nombre, argumentos)
    assert respuesta["ok"], respuesta
    return respuesta["result"]


@pytest.fixture
def sesion():
    s = api.Sesion()
    llamar(s, "create_sketch", plane="XY", name="Rotulo")
    return s


def agregar(sesion, **opciones):
    resultado = llamar(sesion, "add_text", text="I", **opciones)
    return next(e["id"] for e in resultado["entities"] if e["type"] == "text")


def resuelto(sesion):
    return boceto_activo(sesion, None)[1].boceto


@pytest.mark.parametrize("esquina, pivote", [
    ("bl", (10, 20)), ("br", (50, 20)), ("tl", (10, 30)),
    ("tr", (50, 30)), ("center", (30, 25)),
])
@pytest.mark.parametrize("al_crear", [True, False])
def test_giro_de_marco_alrededor_de_sus_esquinas(sesion, esquina, pivote, al_crear):
    opciones = {"frame": True, "box_width": 40, "frame_height": 10, "x": 10, "y": 20}
    if al_crear:
        opciones.update(angle=90, pivot=f"corner:{esquina}")
    tid = agregar(sesion, **opciones)
    if not al_crear:
        llamar(sesion, "edit_text", entity=tid, angle=90, pivot=f"corner:{esquina}")
    b = resuelto(sesion)
    assert b.esquina_marco(tid, esquina) == pytest.approx(pivote, abs=1e-8)
    px, py = pivote
    assert b.coords(b.curvas[tid].punto) == pytest.approx((px - (20 - py), py + (10 - px)), abs=1e-8)
    assert b.curvas[tid].angulo == pytest.approx(90)
    lados = [c for c in b.curvas.values() if c.tipo == "linea" and c.construccion]
    assert len(lados) == 4
    assert sorted(math.dist(b.coords(c.p1), b.coords(c.p2)) for c in lados) == pytest.approx([10, 10, 40, 40])


def test_giro_absoluto_desde_marco_ya_girado(sesion):
    tid = agregar(sesion, frame=True, box_width=40, frame_height=10, x=10, y=20, angle=30)
    pivote = resuelto(sesion).esquina_marco(tid, "tr")
    origen = resuelto(sesion).coords(resuelto(sesion).curvas[tid].punto)
    llamar(sesion, "edit_text", entity=tid, angle=120, pivot="corner:tr")
    b = resuelto(sesion)
    assert b.esquina_marco(tid, "tr") == pytest.approx(pivote, abs=1e-8)
    assert b.coords(b.curvas[tid].punto) == pytest.approx(
        (pivote[0] - (origen[1] - pivote[1]), pivote[1] + (origen[0] - pivote[0])), abs=1e-8)
    assert b.curvas[tid].angulo == pytest.approx(120)


def test_pivote_explicito_al_crear(sesion):
    tid = agregar(sesion, x=10, y=20, angle=90, pivot=[0, 0])
    assert resuelto(sesion).coords(resuelto(sesion).curvas[tid].punto) == pytest.approx((-20, 10), abs=1e-8)


@pytest.mark.parametrize("herramienta", ["add_text", "edit_text"])
@pytest.mark.parametrize("opciones", [
    {"pivot": "corner:otra"}, {"pivot": "corner:tr", "frame": False},
    {"pivot": [0]}, {"pivot": [math.nan, 0]},
])
def test_pivote_invalido_es_atomico(sesion, herramienta, opciones):
    opciones = dict(opciones)
    marco = opciones.pop("frame", True)
    argumentos = {"angle": 45, **opciones}
    if herramienta == "add_text":
        argumentos.update(text="I", frame=marco)
    else:
        argumentos["entity"] = agregar(sesion, frame=marco, box_width=40, frame_height=10)
    antes = sesion.doc.a_dict()
    respuesta = api.llamar(sesion, herramienta, argumentos)
    assert not respuesta["ok"] and respuesta["error_kind"] in ("INVALID_ARGUMENTS", "INVALID_GEOMETRY"), respuesta
    assert sesion.doc.a_dict() == antes


def test_parametro_texto_es_literal_y_no_acepta_operaciones_numericas():
    tabla = TablaParametros()
    tabla.agregar("ancho", "20 mm")
    tabla.agregar("rotulo", "ancho", tipo="texto")
    tabla.agregar("digitos", "123", tipo="texto")
    assert tabla.valores() == {"ancho": 20, "rotulo": "ancho", "digitos": "123"}
    for expresion in ("digitos", "digitos * 2", "rotulo + 1", "min(rotulo, 2)"):
        with pytest.raises(ErrorExpresion):
            tabla.evaluar(expresion)
    tabla.eliminar("ancho")
    tabla.modificar("rotulo", "Pieza {sin_resolver}")
    assert TablaParametros.desde_lista(tabla.a_lista()).valores()["rotulo"] == "Pieza {sin_resolver}"


@pytest.mark.parametrize("contenido", ["Placa A", "123", "", "  'Texto'  ", "Línea 1\nLínea 2"])
def test_crear_y_editar_parametro_texto_por_api(sesion, contenido, tmp_path):
    parametro = llamar(sesion, "create_parameter", name="pieza", expression=contenido, kind="text")
    assert (parametro["value"], parametro["kind"], parametro["unit"]) == (contenido, "text", "")
    llamar(sesion, "set_parameter", name="pieza", expression=contenido + " nueva")
    assert sesion.doc.parametros.valores()["pieza"] == contenido + " nueva"
    ruta = str(tmp_path / "parametros.omnicad")
    llamar(sesion, "save_document", path=ruta)
    otra = api.Sesion()
    llamar(otra, "open_document", path=ruta)
    assert otra.doc.parametros.valores()["pieza"] == contenido + " nueva"
    assert otra.doc.parametros.obtener("pieza").tipo == "texto"


def test_automatico_text_cambia_glifos_y_persiste(sesion, tmp_path):
    tid = agregar(sesion)
    parametros = llamar(sesion, "get_parameters")["parameters"]
    automatico = next((p for p in parametros if p["name"] == "Text"), None)
    assert automatico is not None, parametros
    assert automatico["kind"] == "text" and automatico["value"] == "I"
    assert "Rotulo" in automatico["used_by"]
    assert op_boceto(sesion, None).boceto.curvas[tid].texto == "{Text}"
    cantidad = len(resuelto(sesion).primitivas(tid))
    llamar(sesion, "set_parameter", name="Text", expression="WWW")
    assert resuelto(sesion).curvas[tid].texto == "WWW"
    assert len(resuelto(sesion).primitivas(tid)) > cantidad
    ruta = str(tmp_path / "texto.omnicad")
    llamar(sesion, "save_document", path=ruta)
    otra = api.Sesion()
    llamar(otra, "open_document", path=ruta)
    assert otra.doc.parametros.valores()["Text"] == "WWW"
    assert resuelto(otra).curvas[tid].texto == "WWW"
    llamar(otra, "set_parameter", name="Text", expression="I")
    assert len(resuelto(otra).primitivas(tid)) == cantidad


def test_parametro_texto_se_referencia_con_llaves(sesion):
    llamar(sesion, "create_parameter", name="pieza", expression="ABC", kind="text")
    resultado = llamar(sesion, "add_text", text="Pieza {pieza}")
    tid = resultado["entities"][0]["id"]
    assert resuelto(sesion).curvas[tid].texto == "Pieza ABC"


def test_receta_vieja_sin_parametros_de_texto_sigue_abriendo(sesion):
    from omnicad.timeline.documento import Documento

    op_boceto(sesion, None).boceto.agregar_texto((10, 20), "Antiguo", altura=5)
    receta = sesion.doc.a_dict()
    documento = Documento.desde_dict(receta)
    documento.recalcular()
    texto = next(c for c in documento.estado_final.bocetos["op1"].boceto.curvas.values() if c.tipo == "texto")
    assert texto.texto == "Antiguo" and texto.altura == pytest.approx(5)


def test_sustitucion_de_cadenas_conserva_literal_y_formato_numerico():
    from omnicad.timeline.operaciones import texto_con_valores

    valores = {"pieza": "123 {ancho}", "ancho": 20.25}
    assert texto_con_valores("{pieza:.1f} / {ancho:.1f}", valores) == "123 {ancho} / 20.2"
    assert texto_con_valores("{'Pieza ' + pieza + ' / ' + ancho}", valores) == "Pieza 123 {ancho} / 20.25"


def test_text_automatico_no_pisa_nombres_y_deshace_en_un_paso(sesion):
    llamar(sesion, "create_parameter", name="Text", expression="20 mm")
    primero = agregar(sesion)
    segundo = agregar(sesion, x=20)
    assert sesion.doc.parametros.valores() == {"Text": 20, "Text_1": "I", "Text_2": "I"}
    assert op_boceto(sesion, None).boceto.curvas[primero].texto == "{Text_1}"
    assert op_boceto(sesion, None).boceto.curvas[segundo].texto == "{Text_2}"
    llamar(sesion, "undo")
    assert segundo not in resuelto(sesion).curvas
    assert sesion.doc.parametros.valores() == {"Text": 20, "Text_1": "I"}
    llamar(sesion, "redo")
    assert len(resuelto(sesion).curvas) == 2
    assert sesion.doc.parametros.valores()["Text_2"] == "I"


def test_giro_mueve_cuatro_esquinas_sin_arrastrar_linea_ajena():
    from omnicad.restricciones.boceto import Boceto

    b = Boceto()
    tid = b.agregar_texto((10, 20), "I")
    lados = b.agregar_marco_texto(tid, 40, 10)
    der = b.curvas[tid].marco[0]
    ajena = b.agregar_linea(der, (80, 20), construccion=True)
    punta = b.curvas[ajena].p2
    esquinas = b.puntos_de(lados)
    antes = {p: b.coords(p) for p in esquinas}
    assert set(b._lineas_auxiliares(b.curvas[tid])) == set(lados)
    b.girar_texto(tid, 90, (30, 25))
    for p, (x, y) in antes.items():
        assert b.coords(p) == pytest.approx((30 - (y - 25), 25 + (x - 30)), abs=1e-8)
    assert b.coords(punta) == (80, 20)


def test_text_automatico_con_expresiones_sigue_parametros_y_edicion(sesion, tmp_path):
    llamar(sesion, "create_parameter", name="ancho", expression="20 mm")
    resultado = llamar(sesion, "add_text", text="Ancho {ancho:.1f}")
    tid = resultado["entities"][0]["id"]
    assert sesion.doc.parametros.valores()["Text"] == "Ancho {ancho:.1f}"
    assert resuelto(sesion).curvas[tid].texto == "Ancho 20.0"
    llamar(sesion, "set_parameter", name="ancho", expression="30 mm")
    assert resuelto(sesion).curvas[tid].texto == "Ancho 30.0"
    llamar(sesion, "edit_text", entity=tid, text="Medida {ancho}")
    assert sesion.doc.parametros.valores()["Text"] == "Medida {ancho}"
    assert resuelto(sesion).curvas[tid].texto == "Medida 30"
    llamar(sesion, "create_parameter", name="alto", expression="10 mm")
    llamar(sesion, "set_parameter", name="Text", expression="Alto {alto}")
    assert resuelto(sesion).curvas[tid].texto == "Alto 10"
    respuesta = api.llamar(sesion, "delete_parameter", {"name": "alto"})
    assert not respuesta["ok"]
    ruta = str(tmp_path / "plantilla.omnicad")
    llamar(sesion, "save_document", path=ruta)
    otra = api.Sesion()
    llamar(otra, "open_document", path=ruta)
    llamar(otra, "set_parameter", name="alto", expression="15 mm")
    assert resuelto(otra).curvas[tid].texto == "Alto 15"


def test_parametro_automatico_se_revierte_si_falla_el_dibujo(sesion):
    antes = sesion.doc.a_dict()
    respuesta = api.llamar(sesion, "add_text", {"text": "I", "x": 2e6})
    assert not respuesta["ok"], respuesta
    assert sesion.doc.a_dict() == antes


def test_editar_texto_se_revierte_si_falla_el_giro(sesion):
    tid = agregar(sesion, x=10, y=20)
    punto = resuelto(sesion).curvas[tid].punto
    llamar(sesion, "add_constraint", sketch="Rotulo", type="fix", entities=[punto])
    antes = sesion.doc.a_dict()
    respuesta = api.llamar(sesion, "edit_text", {"entity": tid, "text": "Otro", "angle": 90, "pivot": [0, 0]})
    assert not respuesta["ok"], respuesta
    assert sesion.doc.a_dict() == antes


def test_plantilla_invalida_en_text_muestra_el_contenido_actual(sesion):
    tid = agregar(sesion)
    respuesta = api.llamar(sesion, "set_parameter", {"name": "Text", "expression": "Ancho {no_existe}"})
    assert respuesta["ok"] and any("no_existe" in aviso for aviso in respuesta["avisos"])
    assert resuelto(sesion).curvas[tid].texto == "Ancho {no_existe}"
