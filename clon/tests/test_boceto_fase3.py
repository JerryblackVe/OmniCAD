"""BOC-6: intención de diseño consultable y referencias del marco del boceto."""
import math

import pytest

from omnicad import api
from omnicad.restricciones import Boceto
from omnicad.timeline.operaciones import OpBoceto


def llamar(sesion, nombre, **argumentos):
    respuesta = api.llamar(sesion, nombre, argumentos)
    assert respuesta["ok"], respuesta
    return respuesta["result"]


@pytest.fixture
def sesion():
    s = api.Sesion()
    llamar(s, "create_sketch", name="Base")
    return s


def test_boc6_rectangulo_anclado_y_acotado_informa_estados(sesion):
    dibujo = llamar(sesion, "draw_rectangle", x1=0, y1=0, x2=20, y2=10)
    assert dibujo["dof"] == 2
    info = llamar(sesion, "get_sketch")
    assert info["conflicts"] == []
    assert [p["state"] for p in info["points"]] == ["fixed", "free", "free", "free"]
    assert {c["state"] for c in info["entities"]} == {"free"}
    abajo, derecha = [c["id"] for c in dibujo["entities"][:2]]
    llamar(sesion, "add_dimension", sketch="Base", type="distance", entities=[abajo], value=30)
    parcial = llamar(sesion, "get_sketch")
    assert parcial["dof"] == 1
    assert parcial["entities"][0]["state"] == "determined"
    llamar(sesion, "add_dimension", sketch="Base", type="distance", entities=[derecha], value=15)
    info = llamar(sesion, "get_sketch")
    assert info["dof"] == 0
    assert [p["state"] for p in info["points"]] == ["fixed", "determined", "determined", "determined"]
    assert {c["state"] for c in info["entities"]} == {"determined"}
    assert info["profiles"][0]["area"] == pytest.approx(450)


@pytest.mark.parametrize("sobre_curva", [False, True])
def test_boc6_fix_doble_es_noop_incluso_en_el_historial(sesion, sobre_curva):
    dibujo = llamar(sesion, "draw_line", start_x=3, start_y=4, end_x=8, end_y=9)
    entidad = dibujo["entities"][0]["id"] if sobre_curva else dibujo["points"][0]
    primero = llamar(sesion, "add_constraint", sketch="Base", type="fix", entities=[entidad])
    antes = sesion.doc.a_dict()
    historial = len(sesion.doc._deshacer)
    segundo = llamar(sesion, "add_constraint", sketch="Base", type="fix", entities=[entidad])
    assert segundo["constraint"] == primero["constraint"]
    assert sesion.doc.a_dict() == antes
    assert len(sesion.doc._deshacer) == historial
    info = llamar(sesion, "get_sketch")
    assert len(info["constraints"]) == 1
    assert info["dof"] == (0 if sobre_curva else 2)
    assert info["entities"][0]["state"] == ("fixed" if sobre_curva else "free")


def test_boc6_origen_y_ejes_son_citables_sin_mutar_al_consultar(sesion):
    antes = sesion.doc.a_dict()
    info = llamar(sesion, "get_sketch")
    assert info["origin"] == 0
    assert info["axes"] == {"x": -1, "y": -2}
    assert sesion.doc.a_dict() == antes
    dibujo = llamar(sesion, "draw_point", x=3, y=4)
    punto = dibujo["points"][0]
    resultado = llamar(sesion, "add_constraint", sketch="Base", type="coincident", entities=[punto, info["origin"]])
    assert resultado["dof"] == 0
    info = llamar(sesion, "get_sketch")
    p = next(p for p in info["points"] if p["id"] == punto)
    assert (p["x"], p["y"], p["state"]) == (0, 0, "fixed")


@pytest.mark.parametrize("tipo,referencia,coordenada", [
    ("horizontal", 0, "y"), ("vertical", 0, "x"),
    ("coincident", -1, "y"), ("coincident", -2, "x"),
])
def test_boc6_restricciones_con_el_marco(sesion, tipo, referencia, coordenada):
    punto = llamar(sesion, "draw_point", x=3, y=4)["points"][0]
    resultado = llamar(sesion, "add_constraint", sketch="Base", type=tipo, entities=[punto, referencia])
    assert resultado["dof"] == 1
    info = llamar(sesion, "get_sketch")
    assert next(p for p in info["points"] if p["id"] == punto)[coordenada] == pytest.approx(0)
    assert info["profiles"] == []


@pytest.mark.parametrize("referencia,valor", [(0, 5), (-1, 4), (-2, 3)])
def test_boc6_cotas_al_marco_y_serializacion(sesion, referencia, valor):
    punto = llamar(sesion, "draw_point", x=3, y=4)["points"][0]
    cota = llamar(sesion, "add_dimension", sketch="Base", type="distance", entities=[referencia, punto])
    assert cota["dimension"]["value"] == pytest.approx(valor)
    assert cota["dof"] == 1
    b = sesion.doc.operaciones[0].boceto
    assert Boceto.desde_dict(b.a_dict()).a_dict() == b.a_dict()
    llamar(sesion, "edit_dimension", sketch="Base", dimension=cota["dimension"]["id"], value=2 * valor)
    info = llamar(sesion, "get_sketch")
    assert info["dimensions"][0]["value"] == pytest.approx(2 * valor)
    assert info["dof"] == 1


def test_boc6_conflictos_incluye_fijacion_y_cota_sin_mutar_receta():
    s = api.Sesion()
    b = Boceto()
    linea = b.agregar_linea((0, 0), (10, 0))
    fijo = b.agregar_restriccion("fijo", [linea])
    cota = b.agregar_cota("distancia", [linea], "20")
    s.doc.agregar(OpBoceto(s.doc.nuevo_id(), "En conflicto", boceto=b))
    antes = s.doc.a_dict()
    info = llamar(s, "get_sketch")
    assert info["status"] == "over_constrained"
    assert set(info["conflicts"]) == {fijo, cota}
    assert s.doc.a_dict() == antes


def test_boc6_dos_cotas_en_choque_no_senalan_restricciones_ajenas():
    s = api.Sesion()
    b = Boceto()
    linea = b.agregar_linea((1, 1), (11, 1))
    b.agregar_restriccion("horizontal", [linea])
    cotas = {b.agregar_cota("distancia", [linea], v) for v in ("10", "20")}
    s.doc.agregar(OpBoceto(s.doc.nuevo_id(), "En conflicto", boceto=b))
    assert set(llamar(s, "get_sketch")["conflicts"]) == cotas


def test_boc6_fix_de_varias_entidades_es_idempotente_en_cualquier_orden(sesion):
    dibujo = llamar(sesion, "draw_line", start_x=3, start_y=4, end_x=8, end_y=9)
    primero = llamar(sesion, "add_constraint", sketch="Base", type="fix", entities=dibujo["points"])
    antes = sesion.doc.a_dict()
    segundo = llamar(sesion, "add_constraint", sketch="Base", type="fix", entities=dibujo["points"][::-1])
    assert segundo == primero
    assert sesion.doc.a_dict() == antes


def test_boc6_fijar_el_anclaje_automatico_reutiliza_su_restriccion(sesion):
    dibujo = llamar(sesion, "draw_rectangle", x1=0, y1=0, x2=20, y2=10)
    info = llamar(sesion, "get_sketch")
    fijo = next(r for r in info["constraints"] if r["type"] == "fix")
    historial = len(sesion.doc._deshacer)
    resultado = llamar(sesion, "add_constraint", sketch="Base", type="fix", entities=[dibujo["points"][0]])
    assert resultado["constraint"] == fijo
    assert len(sesion.doc._deshacer) == historial


@pytest.mark.parametrize("argumentos,gdl", [
    ({"origin_x": 0, "origin_y": 0, "width": 20, "height": 10}, 2),
    ({"center_x": 0, "center_y": 0, "width": 20, "height": 10, "center_diagonals": True}, 2),
    ({"three_points": [[0, 0], [20, 0], [20, 10]]}, 3),
    ({"x1": 1, "y1": 2, "x2": 21, "y2": 12}, 4),
])
def test_boc6_variantes_de_rectangulo_comparten_criterio_de_anclaje(sesion, argumentos, gdl):
    resultado = llamar(sesion, "draw_rectangle", **argumentos)
    assert resultado["dof"] == gdl
    info = llamar(sesion, "get_sketch")
    assert info["profiles"][0]["area"] == pytest.approx(200)
    assert sum(p["state"] == "fixed" for p in info["points"]) == (0 if gdl == 4 else 1)


def test_boc6_referencias_no_cambian_ids_ni_encadenan_extremos_auxiliares(sesion):
    punto = llamar(sesion, "draw_point", x=3, y=4)["points"][0]
    llamar(sesion, "add_constraint", sketch="Base", type="coincident", entities=[punto, -1])
    dibujo = llamar(sesion, "draw_line", start_x=1, start_y=0, end_x=8, end_y=9)
    assert all(p > 0 for p in dibujo["points"])
    assert dibujo["dof"] == 5
    antes = llamar(sesion, "get_sketch")
    llamada = api.llamar(sesion, "delete_sketch_entities", {"entities": [-1]})
    assert not llamada["ok"]
    assert llamada["error_kind"] == "INVALID_GEOMETRY"
    assert llamar(sesion, "get_sketch") == antes


def test_boc6_referencia_invalida_no_materializa_el_marco(sesion):
    antes = sesion.doc.a_dict()
    resultado = api.llamar(sesion, "add_constraint", {"sketch": "Base", "type": "coincident", "entities": [999, 0]})
    assert resultado["error_kind"] == "ENTITY_NOT_FOUND"
    assert sesion.doc.a_dict() == antes


def test_boc6_conflicto_por_colapso_usa_la_geometria_original():
    s = api.Sesion()
    b = Boceto()
    linea = b.agregar_linea((0, 0), (0, 10))
    horizontal = b.agregar_restriccion("horizontal", [linea])
    s.doc.agregar(OpBoceto(s.doc.nuevo_id(), "Colapso", boceto=b))
    info = llamar(s, "get_sketch")
    assert info["status"] == "over_constrained"
    assert info["conflicts"] == [horizontal]


def test_boc6_anclaje_de_la_ui_delega_en_el_boceto():
    from omnicad.ui.editor_boceto import Lienzo

    class LienzoSimulado:
        b = Boceto()

    lienzo = LienzoSimulado()
    punto = lienzo.b.agregar_punto(0, 0)
    restriccion = Lienzo._anclar_al_origen(lienzo, {punto})
    assert lienzo.b.restricciones[restriccion].entidades == [punto]
    assert lienzo.b.restricciones[restriccion].datos == {"origen": True}


def _rectangulo_boc2(sesion, segunda=True):
    dibujo = llamar(sesion, "draw_rectangle", x1=0, y1=0, x2=20, y2=10)
    lados = [c["id"] for c in dibujo["entities"][:2]]
    primera = llamar(sesion, "add_dimension", sketch="Base", type="distance", entities=lados[:1], value=20)
    if segunda:
        llamar(sesion, "add_dimension", sketch="Base", type="distance", entities=lados[1:], value="d1/2")
    return primera["dimension"]


def _parametros_boc2(sesion):
    return {p["name"]: p for p in llamar(sesion, "get_parameters")["parameters"]}


def test_boc2_cotas_son_parametros_y_mueven_geometria_y_operaciones(sesion):
    primera = _rectangulo_boc2(sesion)
    assert primera["name"] == "d1"
    parametros = _parametros_boc2(sesion)
    assert list(parametros) == ["d1", "d2"]
    assert [(p["source"], p["sketch"], p["value"]) for p in parametros.values()] == [
        ("sketch", "op1", 20), ("sketch", "op1", 10)]
    assert parametros["d1"]["dimension"] == primera["id"]
    llamar(sesion, "create_parameter", name="altura", expression="d2/2")
    llamar(sesion, "extrude", sketch="Base", distance="altura")
    llamar(sesion, "set_parameter", name="d1", expression=40)
    info = llamar(sesion, "get_sketch", sketch="Base")
    assert info["dof"] == 0 and info["status"] == "fully_constrained"
    assert {c["state"] for c in info["entities"]} == {"determined"}
    assert [c["value"] for c in info["dimensions"]] == [40, 20]
    assert info["profiles"][0]["area"] == pytest.approx(800)
    assert llamar(sesion, "get_scene_info")["bodies"][0]["volume"] == pytest.approx(8000)
    assert _parametros_boc2(sesion)["altura"]["value"] == 10
    editada = llamar(sesion, "edit_dimension", dimension=primera["id"], sketch="Base", value=30)
    assert editada["dimension"]["name"] == "d1"
    assert _parametros_boc2(sesion)["d1"]["value"] == 30
    assert _parametros_boc2(sesion)["d2"]["value"] == 15


def test_boc2_guardar_abrir_y_deshacer_rehacer(sesion, tmp_path):
    _rectangulo_boc2(sesion)
    antes = sesion.doc.a_dict()
    llamar(sesion, "set_parameter", name="d1", expression=40)
    despues = sesion.doc.a_dict()
    llamar(sesion, "undo")
    assert sesion.doc.a_dict() == antes
    llamar(sesion, "redo")
    assert sesion.doc.a_dict() == despues
    ruta = str(tmp_path / "cotas.omnicad")
    llamar(sesion, "save_document", path=ruta)
    otra = api.Sesion()
    llamar(otra, "open_document", path=ruta)
    assert [p["value"] for p in _parametros_boc2(otra).values()] == [40, 20]
    info = llamar(otra, "get_sketch")
    assert [(c["name"], c["value"]) for c in info["dimensions"]] == [("d1", 40), ("d2", 20)]
    assert info["profiles"][0]["area"] == pytest.approx(800)
    llamar(otra, "set_parameter", name="d1", expression=60)
    assert llamar(otra, "get_sketch")["profiles"][0]["area"] == pytest.approx(1800)


@pytest.mark.parametrize("herramienta,argumentos", [
    ("delete_parameter", {"name": "d1"}),
    ("delete_sketch_entities", {}),
    ("delete_feature", {"feature": "Base"}),
])
def test_boc2_borrado_en_uso_es_atomico(sesion, herramienta, argumentos):
    primera = _rectangulo_boc2(sesion)
    llamar(sesion, "create_parameter", name="dependiente", expression="d1*2")
    if herramienta == "delete_sketch_entities":
        argumentos = {"entities": [primera["id"]]}
    antes = sesion.doc.a_dict()
    historial = list(sesion.doc._deshacer)
    resultado = api.llamar(sesion, herramienta, argumentos)
    assert resultado["ok"] is False, resultado
    assert resultado["error_kind"] == "PARAMETER_IN_USE", resultado
    assert "d1" in resultado["mensaje"]
    assert sesion.doc.a_dict() == antes
    assert sesion.doc._deshacer == historial


@pytest.mark.parametrize("borrar_boceto", [False, True])
def test_boc2_borrar_cota_o_boceto_quita_parametro_con_deshacer(sesion, borrar_boceto):
    primera = _rectangulo_boc2(sesion, segunda=False)
    assert _parametros_boc2(sesion)["d1"]["value"] == 20
    if borrar_boceto:
        llamar(sesion, "delete_feature", feature="Base")
    else:
        llamar(sesion, "delete_sketch_entities", entities=[primera["id"]])
    assert _parametros_boc2(sesion) == {}
    llamar(sesion, "undo")
    assert _parametros_boc2(sesion)["d1"]["value"] == 20
    llamar(sesion, "redo")
    assert _parametros_boc2(sesion) == {}


@pytest.mark.parametrize("herramienta,expresion", [
    ("edit_dimension", "d1+1"), ("edit_dimension", "d2*2"),
    ("set_parameter", "d1+1"), ("set_parameter", "d2*2"),
])
def test_boc2_ciclos_directos_e_indirectos_no_cambian_nada(sesion, herramienta, expresion):
    primera = _rectangulo_boc2(sesion)
    argumentos = ({"dimension": primera["id"], "value": expresion} if herramienta == "edit_dimension"
                  else {"name": "d1", "expression": expresion})
    antes = sesion.doc.a_dict()
    resultado = api.llamar(sesion, herramienta, argumentos)
    assert resultado["error_kind"] == "CIRCULAR_REFERENCE", resultado
    assert sesion.doc.a_dict() == antes


def test_boc2_nombres_unicos_entre_bocetos_sin_colision(sesion):
    llamar(sesion, "create_parameter", name="d1", expression=7)
    llamar(sesion, "create_parameter", name="d3", expression=9)
    primera = _rectangulo_boc2(sesion, segunda=False)
    assert primera["name"] == "d2"
    llamar(sesion, "create_sketch", name="Otro")
    curva = llamar(sesion, "draw_circle", center_x=0, center_y=0, radius=3)["entities"][0]["id"]
    segunda = llamar(sesion, "add_dimension", sketch="Otro", type="radius", entities=[curva], value="d2/2")
    assert segunda["dimension"]["name"] == "d4"
    llamar(sesion, "set_parameter", name="d2", expression=40)
    assert llamar(sesion, "get_sketch", sketch="Otro")["dimensions"][0]["value"] == 20
    assert _parametros_boc2(sesion)["d1"]["value"] == 7


def test_boc2_cota_con_expresion_se_evalua_como_parametro(sesion):
    llamar(sesion, "create_parameter", name="ancho", expression=30)
    dibujo = llamar(sesion, "draw_line", start_x=0, start_y=0, end_x=10, end_y=0)
    cota = llamar(sesion, "add_dimension", sketch="Base", type="distance",
                  entities=[dibujo["entities"][0]["id"]], value="ancho/2")["dimension"]
    assert _parametros_boc2(sesion)["d1"]["value"] == 15
    llamar(sesion, "set_parameter", name="ancho", expression=40)
    assert _parametros_boc2(sesion)["d1"]["value"] == 20
    llamar(sesion, "edit_dimension", dimension=cota["id"], value="ancho/4")
    assert _parametros_boc2(sesion)["d1"]["value"] == 10


def test_boc2_receta_vieja_asigna_nombres_estables_sin_mutar_al_recalcular():
    from omnicad.timeline.documento import Documento

    b = Boceto()
    linea = b.agregar_linea((0, 0), (10, 0))
    b.agregar_cota("distancia", [linea], "10")
    receta = {"operaciones": [OpBoceto("op1", "Viejo", boceto=b).a_dict()]}
    s = api.Sesion(Documento.desde_dict(receta))
    assert _parametros_boc2(s)["d1"]["value"] == 10
    antes = s.doc.a_dict()
    s.doc.recalcular()
    assert s.doc.a_dict() == antes
    assert Documento.desde_dict(antes).a_dict() == antes


def test_boc2_editar_cota_posterior_recalcula_boceto_anterior(sesion):
    primera = _rectangulo_boc2(sesion, segunda=False)
    llamar(sesion, "create_sketch", name="Otro")
    curva = llamar(sesion, "draw_circle", center_x=0, center_y=0, radius=3)["entities"][0]["id"]
    segunda = llamar(sesion, "add_dimension", sketch="Otro", type="radius", entities=[curva], value=10)["dimension"]
    llamar(sesion, "edit_dimension", sketch="Base", dimension=primera["id"], value="d2*2")
    llamar(sesion, "edit_dimension", sketch="Otro", dimension=segunda["id"], value=20)
    assert llamar(sesion, "get_sketch", sketch="Base")["profiles"][0]["area"] == pytest.approx(400)
    assert _parametros_boc2(sesion)["d1"]["value"] == 40


def test_boc2_configuracion_sincroniza_cota_y_receta(sesion):
    _rectangulo_boc2(sesion)
    llamar(sesion, "manage_configurations", action="set", columns=[{"type": "parameter", "name": "d1"}],
           rows=[{"name": "Grande", "values": [40]}])
    llamar(sesion, "manage_configurations", action="apply", row="Grande")
    info = llamar(sesion, "get_sketch")
    assert [c["value"] for c in info["dimensions"]] == [40, 20]
    assert info["dimensions"][0]["expression"] == "40"
    assert info["profiles"][0]["area"] == pytest.approx(800)
    llamar(sesion, "draw_point", x=100, y=100)
    assert _parametros_boc2(sesion)["d1"]["value"] == 40


def test_boc2_previa_de_cota_editada_no_usa_valor_anterior(sesion):
    primera = _rectangulo_boc2(sesion, segunda=False)
    op = sesion.doc.operaciones[0].copia()
    op.boceto.cotas[primera["id"]].expresion = "40"
    antes = sesion.doc.a_dict()
    estado, avisos = sesion.doc.previsualizar(op, 0)
    assert avisos == []
    assert estado.bocetos[op.id].perfiles[0].area == pytest.approx(400)
    assert sesion.doc.a_dict() == antes


@pytest.mark.parametrize("dependiente", ["parameter", "operation", "sketch"])
def test_boc2_borrar_cota_usada_solo_por_expresion_ajena(sesion, dependiente):
    primera = _rectangulo_boc2(sesion, segunda=False)
    if dependiente == "parameter":
        llamar(sesion, "create_parameter", name="otra", expression="d1/2")
    elif dependiente == "operation":
        llamar(sesion, "create_box", length="d1", width=2, height=3)
    else:
        llamar(sesion, "create_sketch", name="Otro")
        curva = llamar(sesion, "draw_circle", center_x=0, center_y=0, radius=3)["entities"][0]["id"]
        llamar(sesion, "add_dimension", sketch="Otro", type="radius", entities=[curva], value="d1/2")
    antes = sesion.doc.a_dict()
    resultado = api.llamar(sesion, "delete_sketch_entities", {"sketch": "Base", "entities": [primera["id"]]})
    assert resultado["error_kind"] == "PARAMETER_IN_USE", resultado
    assert sesion.doc.a_dict() == antes


def test_boc2_borrado_de_curva_limpia_parametro_sin_reutilizar_nombre(sesion):
    primera = _rectangulo_boc2(sesion, segunda=False)
    llamar(sesion, "delete_sketch_entities", entities=primera["entities"])
    assert _parametros_boc2(sesion) == {}
    linea = llamar(sesion, "draw_line", start_x=100, start_y=100, end_x=110, end_y=100)["entities"][0]["id"]
    nueva = llamar(sesion, "add_dimension", sketch="Base", type="distance", entities=[linea], value=10)
    assert nueva["dimension"]["name"] == "d2"


def test_boc2_cota_angular_es_parametro_en_grados(sesion):
    linea1 = llamar(sesion, "draw_line", start_x=0, start_y=0, end_x=10, end_y=0)["entities"][0]["id"]
    linea2 = llamar(sesion, "draw_line", start_x=0, start_y=0, end_x=10, end_y=10)["entities"][0]["id"]
    llamar(sesion, "add_dimension", sketch="Base", type="angle", entities=[linea1, linea2], value="45 deg")
    parametro = _parametros_boc2(sesion)["d1"]
    assert (parametro["kind"], parametro["unit"], parametro["value"]) == ("angle", "deg", 45)
    llamar(sesion, "set_parameter", name="d1", expression="60 deg")
    assert llamar(sesion, "get_sketch")["dimensions"][0]["value"] == 60


def test_boc2_borrar_boceto_con_cotas_dependientes_entre_si(sesion):
    _rectangulo_boc2(sesion)
    llamar(sesion, "delete_feature", feature="Base")
    assert _parametros_boc2(sesion) == {}
    llamar(sesion, "undo")
    assert [p["value"] for p in _parametros_boc2(sesion).values()] == [20, 10]


def test_boc2_previa_con_ciclo_informa_el_ciclo_y_no_muta(sesion):
    from omnicad.timeline.parametros import ErrorExpresion

    primera = _rectangulo_boc2(sesion, segunda=False)
    op = sesion.doc.operaciones[0].copia()
    op.boceto.cotas[primera["id"]].expresion = "d1+1"
    antes = sesion.doc.a_dict()
    with pytest.raises(ErrorExpresion, match="circular"):
        sesion.doc.previsualizar(op, 0)
    assert sesion.doc.a_dict() == antes


def _linea_boc1(sesion):
    dibujo = llamar(sesion, "draw_line", start_x=0, start_y=0, end_x=40, end_y=0)
    linea = dibujo["entities"][0]["id"]
    llamar(sesion, "add_constraint", sketch="Base", type="horizontal", entities=[linea])
    return linea


@pytest.mark.parametrize("tipo,valor", [("distance", 40), ("distance", 70), ("horizontal", 40)])
def test_boc1_cota_redundante_o_contradictoria_se_crea_como_referencia(sesion, tipo, valor):
    linea = _linea_boc1(sesion)
    primera = llamar(sesion, "add_dimension", sketch="Base", type="distance", entities=[linea], value=40)
    antes = llamar(sesion, "get_sketch")
    respuesta = api.llamar(sesion, "add_dimension", {"sketch": "Base", "type": tipo, "entities": [linea], "value": valor})
    assert respuesta["ok"], respuesta
    r = respuesta["result"]
    assert r["converted_to_reference"] is True
    assert respuesta["avisos"] and "referencia" in " ".join(respuesta["avisos"]).lower()
    assert r["dimension"]["reference"] is True
    assert r["dimension"]["value"] == pytest.approx(40)
    assert r["dimension"]["name"] == "d2"
    assert r["dof"] == primera["dof"] == 2
    despues = llamar(sesion, "get_sketch")
    assert despues["status"] == "under_constrained" and despues["conflicts"] == []
    assert despues["points"] == antes["points"]
    assert [k["reference"] for k in despues["dimensions"]] == [False, True]


def test_boc1_referencia_explicita_mide_sin_restringir_y_alterna(sesion):
    linea = _linea_boc1(sesion)
    referencia = llamar(sesion, "add_dimension", sketch="Base", type="distance", entities=[linea],
                        value=99, reference=True)
    k = referencia["dimension"]
    assert (k["reference"], k["value"], referencia["dof"]) == (True, 40, 3)
    driving = llamar(sesion, "edit_dimension", dimension=k["id"], reference=False)
    assert (driving["dimension"]["reference"], driving["dimension"]["value"], driving["dof"]) == (False, 40, 2)
    llamar(sesion, "edit_dimension", dimension=k["id"], value=60)
    antes = sesion.doc.a_dict()
    driven = llamar(sesion, "edit_dimension", dimension=k["id"], reference=True)
    assert (driven["dimension"]["reference"], driven["dimension"]["value"], driven["dof"]) == (True, 60, 3)
    assert float(driven["dimension"]["expression"]) == pytest.approx(60)
    llamar(sesion, "undo")
    assert sesion.doc.a_dict() == antes
    llamar(sesion, "redo")
    assert llamar(sesion, "get_sketch")["dimensions"][0]["reference"] is True


def test_boc1_alternancia_redundante_avisa_y_no_cambia_documento_ni_historial(sesion):
    linea = _linea_boc1(sesion)
    llamar(sesion, "add_dimension", sketch="Base", type="distance", entities=[linea], value=40)
    k = llamar(sesion, "add_dimension", sketch="Base", type="distance", entities=[linea], reference=True)["dimension"]
    antes, historial = sesion.doc.a_dict(), list(sesion.doc._deshacer)
    respuesta = api.llamar(sesion, "edit_dimension", {"dimension": k["id"], "reference": False})
    assert respuesta["ok"], respuesta
    assert respuesta["result"]["dimension"]["reference"] is True
    assert respuesta["avisos"] and "referencia" in " ".join(respuesta["avisos"]).lower()
    assert sesion.doc.a_dict() == antes
    assert sesion.doc._deshacer == historial


def test_boc1_referencia_sigue_geometria_y_su_parametro_es_citable(sesion, tmp_path):
    linea = _linea_boc1(sesion)
    driving = llamar(sesion, "add_dimension", sketch="Base", type="distance", entities=[linea], value=40)["dimension"]
    driven = llamar(sesion, "add_dimension", sketch="Base", type="distance", entities=[linea], reference=True)["dimension"]
    llamar(sesion, "create_parameter", name="medida", expression="d2/2")
    llamar(sesion, "create_sketch", name="Otro")
    circulo = llamar(sesion, "draw_circle", center_x=0, center_y=0, radius=3)["entities"][0]["id"]
    llamar(sesion, "add_dimension", sketch="Otro", type="radius", entities=[circulo], value="d2/4")
    for herramienta, argumentos, valor in [
        ("edit_dimension", {"dimension": driving["id"], "sketch": "Base", "value": 60}, 60),
        ("set_parameter", {"name": "d1", "expression": 80}, 80),
    ]:
        llamar(sesion, herramienta, **argumentos)
        info = llamar(sesion, "get_sketch", sketch="Base")
        assert [k["value"] for k in info["dimensions"]] == [valor, valor]
        assert info["dimensions"][1]["reference"] is True
        parametros = _parametros_boc2(sesion)
        assert parametros[driven["name"]]["value"] == valor
        assert parametros["medida"]["value"] == valor / 2
        assert llamar(sesion, "get_sketch", sketch="Otro")["dimensions"][0]["value"] == valor / 4
    ruta = str(tmp_path / "referencias.omnicad")
    llamar(sesion, "save_document", path=ruta)
    otra = api.Sesion()
    llamar(otra, "open_document", path=ruta)
    info = llamar(otra, "get_sketch", sketch="Base")
    assert [(k["reference"], k["value"]) for k in info["dimensions"]] == [(False, 80), (True, 80)]
    antes = otra.doc.a_dict()
    otra.doc.recalcular()
    assert otra.doc.a_dict() == antes


@pytest.mark.parametrize("herramienta", ["edit_dimension", "set_parameter"])
def test_boc1_no_se_puede_editar_el_valor_de_referencia(sesion, herramienta):
    linea = _linea_boc1(sesion)
    k = llamar(sesion, "add_dimension", sketch="Base", type="distance", entities=[linea], reference=True)["dimension"]
    antes = sesion.doc.a_dict()
    argumentos = {"dimension": k["id"], "value": 20} if herramienta == "edit_dimension" else {"name": k["name"], "expression": 20}
    r = api.llamar(sesion, herramienta, argumentos)
    assert not r["ok"] and r["error_kind"] == "INVALID_DIMENSION", r
    assert "referencia" in r["mensaje"].lower()
    assert sesion.doc.a_dict() == antes
    movida = llamar(sesion, "edit_dimension", dimension=k["id"], offset=8, text_offset=3)
    assert movida["dimension"]["reference"] is True
    assert movida["dimension"]["value"] == 40


@pytest.mark.parametrize("tipo,entidades,medida", [
    ("distancia", [3], 5), ("distancia_h", [3], 3), ("distancia_v", [3], 4),
    ("radio", [4], 7), ("diametro", [4], 14), ("angulo", [3, 8], 53.1301023542),
    ("desfase", [4, 9], 2),
])
def test_boc1_solver_ignora_referencias_en_todos_los_tipos(tipo, entidades, medida):
    from omnicad.restricciones import resolver

    b = Boceto()
    b.agregar_linea((0, 0), (3, 4))
    b.agregar_circulo((20, 20), 7)
    b.agregar_linea((50, 50), (60, 50))
    b.agregar_circulo((20, 20), 9)
    antes = b.a_dict()
    inicial = resolver(b.copia())
    cid = b.agregar_cota(tipo, entidades, "999", referencia=True)
    res = resolver(b)
    assert res.ok and res.gdl == inicial.gdl == 14
    assert res.residuo_max == 0
    assert b.medir_cota(tipo, entidades) == pytest.approx(medida)
    assert b.a_dict()["puntos"] == antes["puntos"]
    assert b.a_dict()["curvas"] == antes["curvas"]
    copia = Boceto.desde_dict(b.a_dict())
    assert copia.cotas[cid].referencia is True
    assert copia.copia().cotas[cid].referencia is True


def test_boc1_archivos_viejos_siguen_con_cotas_driving():
    b = Boceto()
    linea = b.agregar_linea((0, 0), (10, 0))
    cid = b.agregar_cota("distancia", [linea], "20")
    datos = b.a_dict()
    datos["cotas"][0].pop("referencia", None)
    copia = Boceto.desde_dict(datos)
    assert copia.cotas[cid].referencia is False


def test_boc1_referencia_en_otro_grupo_del_mismo_boceto_y_ciclo_atomico(sesion):
    linea = _linea_boc1(sesion)
    primera = llamar(sesion, "add_dimension", sketch="Base", type="distance", entities=[linea], value=40)["dimension"]
    llamar(sesion, "add_dimension", sketch="Base", type="distance", entities=[linea], reference=True)
    circulo = llamar(sesion, "draw_circle", center_x=100, center_y=0, radius=3)["entities"][0]["id"]
    llamar(sesion, "add_dimension", sketch="Base", type="radius", entities=[circulo], value="d2/4")
    llamar(sesion, "edit_dimension", dimension=primera["id"], value=80)
    info = llamar(sesion, "get_sketch")
    assert [k["value"] for k in info["dimensions"]] == [80, 80, 20]
    assert next(c for c in info["entities"] if c["id"] == circulo)["radius"] == 20
    antes = sesion.doc.a_dict()
    r = api.llamar(sesion, "edit_dimension", {"dimension": primera["id"], "value": "d2/2"})
    assert not r["ok"] and r["error_kind"] == "CIRCULAR_REFERENCE", r
    assert sesion.doc.a_dict() == antes


def test_boc1_conversion_a_referencia_pierde_expresion_y_permite_medida_cero(sesion):
    llamar(sesion, "create_parameter", name="largo", expression=60)
    linea = _linea_boc1(sesion)
    driving = llamar(sesion, "add_dimension", sketch="Base", type="distance", entities=[linea], value="largo")["dimension"]
    driven = llamar(sesion, "edit_dimension", dimension=driving["id"], reference=True)
    assert float(driven["dimension"]["expression"]) == 60
    llamar(sesion, "set_parameter", name="largo", expression=90)
    assert llamar(sesion, "get_sketch")["dimensions"][0]["value"] == 60
    cero = llamar(sesion, "add_dimension", sketch="Base", type="vertical", entities=[linea], reference=True)
    assert cero["dimension"]["reference"] is True
    assert cero["dimension"]["value"] == 0
    antes = sesion.doc.a_dict()
    r = api.llamar(sesion, "edit_dimension", {"dimension": cero["dimension"]["id"], "reference": False})
    assert r["ok"] and r["avisos"], r
    assert r["result"]["dimension"]["reference"] is True
    assert sesion.doc.a_dict() == antes


def test_boc1_referencia_copiada_y_arrastrada_sigue_siendo_libre(sesion):
    linea = _linea_boc1(sesion)
    k = llamar(sesion, "add_dimension", sketch="Base", type="distance", entities=[linea], reference=True)["dimension"]
    info = llamar(sesion, "get_sketch")
    extremo = info["entities"][0]["points"][-1]
    llamar(sesion, "move_sketch_point", point=extremo, x=70, y=0)
    assert llamar(sesion, "get_sketch")["dimensions"][0]["value"] == 70
    assert _parametros_boc2(sesion)[k["name"]]["value"] == 70
    llamar(sesion, "transform_sketch", entities=[linea], copy=True, dx=100)
    info = llamar(sesion, "get_sketch")
    assert [c["reference"] for c in info["dimensions"]] == [True, True]
    assert [c["value"] for c in info["dimensions"]] == [70, 70]
    assert info["dof"] == 6


def _lienzo_boc1():
    import os
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    from PySide6.QtWidgets import QApplication

    from omnicad.nucleo import geometria as g
    from omnicad.timeline.parametros import TablaParametros
    from omnicad.ui.editor_boceto import Lienzo
    QApplication.instance() or QApplication([])
    b = Boceto()
    linea = b.agregar_linea((0, 0), (40, 0))
    b.agregar_restriccion("horizontal", [linea])
    lz = Lienzo(b, TablaParametros().evaluar, plano=g.Plano("XY"))
    lz.resolver()
    return lz, linea


def test_boc1_ui_cota_que_sobra_entra_de_referencia_y_alterna():
    from PySide6.QtCore import QPointF
    lz, linea = _lienzo_boc1()
    for valor in ("40", "40", "70"):                 # la 1.ª restringe; la redundante y la contradictoria miden
        lz._abrir_cota("distancia", [linea], QPointF(100, 100))
        lz.entrada.aceptado.emit([valor])
    primera, segunda, tercera = lz.b.cotas.values()
    assert (primera.referencia, segunda.referencia, tercera.referencia) == (False, True, True)
    assert lz.resultado.ok and lz.resultado.gdl == 2
    assert float(tercera.expresion) == pytest.approx(40)            # mide, no impone el 70
    lz.grab()                                        # se dibuja entre paréntesis
    lz.editar_cota(tercera.id, QPointF(100, 100))    # su valor no se edita
    assert lz.entrada is None
    lz.alternar_referencia(primera.id)               # driving → driven: libera un grado de libertad
    assert primera.referencia and lz.resultado.gdl == 3
    lz.alternar_referencia(primera.id)               # vuelve a driving: ahora restringe otra vez
    assert not primera.referencia and lz.resultado.gdl == 2
    lz.alternar_referencia(segunda.id)               # volver a driving sobre-restringiría: sigue de referencia
    assert lz.b.cotas[segunda.id].referencia and lz.resultado.gdl == 2      # restaurada: objeto nuevo


# ---------------------------------------------------------------- BOC-3: cotas entre curvas y menú de la cota
def _boc3(caso):
    """(boceto, entidades) de cada combinación: punto (10, 0) y círculo centro (0, 0) r=3, etc."""
    b = Boceto()
    if caso in ("punto_circulo", "circulo_punto"):
        c, p = b.agregar_circulo((0, 0), 3), b.agregar_punto(10, 0)
        return b, [p, c] if caso == "punto_circulo" else [c, p]
    if caso == "punto_arco":
        a, p = b.agregar_arco_centro((0, 0), (3, 0), (0, 3)), b.agregar_punto(10, 0)
        return b, [p, a]
    if caso == "circulo_circulo":
        return b, [b.agregar_circulo((0, 0), 3), b.agregar_circulo((20, 0), 2)]
    if caso == "anidados":                           # el chico adentro del grande: 10 - 3 - 3
        return b, [b.agregar_circulo((0, 0), 10), b.agregar_circulo((3, 0), 3)]
    if caso == "linea_circulo":
        return b, [b.agregar_linea((-20, 8), (20, 8)), b.agregar_circulo((0, 0), 3)]
    s = b.agregar_spline([(0, 5), (10, 5), (20, 5)])
    return b, [b.agregar_punto(10, 0), s]


_CASOS_BOC3 = [("punto_circulo", "centro", 10), ("punto_circulo", "tangente", 7), ("circulo_punto", "tangente", 7),
               ("punto_arco", "centro", 10), ("punto_arco", "tangente", 7), ("circulo_circulo", "centro", 20),
               ("circulo_circulo", "tangente", 15), ("anidados", "tangente", 4), ("anidados", "centro", 3),
               ("linea_circulo", "centro", 8), ("linea_circulo", "tangente", 5), ("punto_spline", "centro", 5)]


@pytest.mark.parametrize("caso,modo,medida", _CASOS_BOC3)
def test_boc3_medida_y_solver_de_cada_combinacion(caso, modo, medida):
    from omnicad.restricciones import resolver
    b, ents = _boc3(caso)
    assert b.medir_cota("distancia", ents, modo) == pytest.approx(medida)
    cid = b.agregar_cota("distancia", ents, str(medida + 1.5), {"modo": modo})
    assert b.cotas[cid].datos.get("modo") == (None if caso == "punto_spline" else modo)   # sin centro, sin modo
    res = resolver(b, {cid: medida + 1.5})
    assert res.ok, res.descripcion()
    assert b.medir(b.cotas[cid]) == pytest.approx(medida + 1.5, abs=1e-6)


@pytest.mark.parametrize("caso,fijar,gdl", [("punto_circulo", 1, 1), ("circulo_circulo", 0, 2),
                                            ("linea_circulo", 1, 3), ("punto_spline", 1, 1)])
def test_boc3_la_cota_baja_un_grado_de_libertad(caso, fijar, gdl):
    from omnicad.restricciones import resolver
    b, ents = _boc3(caso)
    b.agregar_restriccion("fijo", [ents[fijar]])
    antes = resolver(b.copia()).gdl
    cid = b.agregar_cota("distancia", ents, "12", {"modo": "centro" if caso == "punto_spline" else "tangente"})
    res = resolver(b, {cid: 12})
    assert res.ok and res.gdl == antes - 1 == gdl


def test_boc3_validacion_del_modelo():
    from omnicad.restricciones import ErrorBoceto
    b, (p, c) = _boc3("punto_circulo")
    q = b.agregar_punto(0, 9)
    e = b.agregar_elipse((40, 0), (50, 0), 4)
    for ents, datos in (([p, q], {"modo": "tangente"}), ([c, c], {}), ([p, c], {"modo": "lado"}), ([c, e], {})):
        with pytest.raises(ErrorBoceto):
            b.agregar_cota("distancia", ents, "5", datos)
    assert b.cotas == {}


def test_boc3_archivo_viejo_sin_modo_mide_al_centro_y_el_modo_se_guarda():
    b, ents = _boc3("punto_circulo")
    cid = b.agregar_cota("distancia", ents, "7", {"modo": "tangente"})
    copia = Boceto.desde_dict(b.a_dict())
    assert copia.cotas[cid].datos["modo"] == "tangente" and copia.medir(copia.cotas[cid]) == pytest.approx(7)
    datos = b.a_dict()
    datos["cotas"][0]["datos"].pop("modo")
    vieja = Boceto.desde_dict(datos)
    assert vieja.medir(vieja.cotas[cid]) == pytest.approx(10)


def _circulo_y_punto_api(sesion):
    circulo = llamar(sesion, "draw_circle", center_x=0, center_y=0, radius=3)["entities"][0]["id"]
    llamar(sesion, "add_constraint", sketch="Base", type="fix", entities=[circulo])
    llamar(sesion, "draw_point", x=10, y=0)
    punto = llamar(sesion, "get_sketch")["points"][-1]["id"]
    return circulo, punto


def test_boc3_api_add_y_edit_con_modo_parametro_y_archivo(sesion, tmp_path):
    circulo, punto = _circulo_y_punto_api(sesion)
    r = llamar(sesion, "add_dimension", sketch="Base", type="distance", entities=[punto, circulo], mode="tangent")
    k = r["dimension"]
    assert (k["mode"], k["value"], r["dof"]) == ("tangent", 7, 1)
    assert llamar(sesion, "get_sketch")["dimensions"][0]["mode"] == "tangent"
    llamar(sesion, "set_parameter", name=k["name"], expression=12)
    p = next(q for q in llamar(sesion, "get_sketch")["points"] if q["id"] == punto)
    assert math.hypot(p["x"], p["y"]) == pytest.approx(15)
    centro = llamar(sesion, "edit_dimension", dimension=k["id"], mode="center")["dimension"]
    assert (centro["mode"], centro["value"]) == ("center", 12)      # conserva la expresión: la geometría la cumple
    p = next(q for q in llamar(sesion, "get_sketch")["points"] if q["id"] == punto)
    assert math.hypot(p["x"], p["y"]) == pytest.approx(12)
    ruta = str(tmp_path / "modo.omnicad")
    llamar(sesion, "save_document", path=ruta)
    otra = api.Sesion()
    llamar(otra, "open_document", path=ruta)
    assert [(c["mode"], c["value"]) for c in llamar(otra, "get_sketch")["dimensions"]] == [("center", 12)]


def test_boc3_api_center_por_defecto_y_errores_claros(sesion):
    circulo, punto = _circulo_y_punto_api(sesion)
    k = llamar(sesion, "add_dimension", sketch="Base", type="distance", entities=[circulo, punto])["dimension"]
    assert (k["mode"], k["value"]) == ("center", 10)
    llamar(sesion, "draw_point", x=0, y=20)
    q = llamar(sesion, "get_sketch")["points"][-1]["id"]
    antes = sesion.doc.a_dict()
    for argumentos in ({"type": "distance", "entities": [punto, q], "mode": "tangent"},
                       {"type": "distance", "entities": [circulo, circulo]},
                       {"type": "horizontal", "entities": [punto, circulo]}):
        r = api.llamar(sesion, "add_dimension", {"sketch": "Base", **argumentos})
        assert not r["ok"] and r["error_kind"] == "INVALID_DIMENSION", r
    r = api.llamar(sesion, "edit_dimension", {"dimension": k["id"], "type": "diameter"})
    assert not r["ok"] and r["error_kind"] == "INVALID_DIMENSION", r
    assert sesion.doc.a_dict() == antes


def test_boc3_api_radio_diametro_conserva_valor_equivalente(sesion):
    llamar(sesion, "create_parameter", name="ag", expression=4)
    circulo = llamar(sesion, "draw_circle", center_x=0, center_y=0, radius=3)["entities"][0]["id"]
    k = llamar(sesion, "add_dimension", sketch="Base", type="radius", entities=[circulo], value="ag")["dimension"]
    d = llamar(sesion, "edit_dimension", dimension=k["id"], type="diameter")["dimension"]
    assert (d["type"], d["value"], d["name"]) == ("diameter", 8, k["name"])
    assert "ag" in d["expression"]
    assert llamar(sesion, "get_sketch")["entities"][0]["radius"] == pytest.approx(4)
    llamar(sesion, "set_parameter", name="ag", expression=5)
    assert llamar(sesion, "get_sketch")["entities"][0]["radius"] == pytest.approx(5)
    r = llamar(sesion, "edit_dimension", dimension=k["id"], type="radius")["dimension"]
    assert (r["type"], r["value"]) == ("radius", 5)
    numerica = llamar(sesion, "add_dimension", sketch="Base", type="diameter", entities=[circulo], reference=True)
    assert numerica["dimension"]["value"] == 10
    radio = llamar(sesion, "edit_dimension", dimension=numerica["dimension"]["id"], type="radius")["dimension"]
    assert (radio["value"], radio["reference"]) == (5, True)


def test_boc3_ui_menu_de_cota_y_herramienta_con_curvas():
    from PySide6.QtCore import QPointF
    lz, _linea = _lienzo_boc1()
    c, p = lz.b.agregar_circulo((60, 0), 3), lz.b.agregar_punto(70, 0)
    lz.b.agregar_restriccion("fijo", [c])
    lz.resolver()
    clics = iter([p, c])
    lz.entidad_en = lambda _pos: next(clics)
    lz.set_herramienta("cota")
    lz._clic_cota(QPointF(10, 10))
    lz._clic_cota(QPointF(20, 20))                   # punto y después círculo: distancia al centro
    lz.entrada.aceptado.emit([""])
    cota = next(k for k in lz.b.cotas.values() if c in k.entidades)
    assert (cota.tipo, cota.datos["modo"], lz.b.medir(cota)) == ("distancia", "centro", pytest.approx(10))
    menu = lz._menu_cota(cota.id)
    assert [a.text() for a in menu.actions() if a.text()] == ["Cota de referencia", "Centro", "Tangente", "Borrar"]
    next(a for a in menu.actions() if a.text() == "Tangente").trigger()
    cota = lz.b.cotas[cota.id]
    assert cota.datos["modo"] == "tangente" and lz.b.medir(cota) == pytest.approx(10)
    assert math.dist(lz.b.coords(p), (60, 0)) == pytest.approx(13)
    next(a for a in lz._menu_cota(cota.id).actions() if a.text() == "Cota de referencia").trigger()
    assert lz.b.cotas[cota.id].referencia
    radio = lz.b.agregar_cota("radio", [c], "3", referencia=True)
    menu = lz._menu_cota(radio)
    assert [a.text() for a in menu.actions() if a.text()] == ["Cota de referencia", "Radio", "Diámetro", "Borrar"]
    next(a for a in menu.actions() if a.text() == "Diámetro").trigger()
    assert lz.b.cotas[radio].tipo == "diametro" and float(lz.b.cotas[radio].expresion) == pytest.approx(6)
    next(a for a in lz._menu_cota(radio).actions() if a.text() == "Borrar").trigger()
    assert radio not in lz.b.cotas


# ---------------------------------------------------------------- BOC-25: cuadrante del ángulo y chaflán ligado
def _dos_lineas_45(sesion, invertida=True):
    """Línea horizontal (0,0)→(10,0) y diagonal a 45°; `invertida` la dibuja de (10,10) hacia el origen."""
    l1 = llamar(sesion, "draw_line", start_x=0, start_y=0, end_x=10, end_y=0)["entities"][0]["id"]
    a, b = ((10, 10), (0, 0)) if invertida else ((0, 0), (10, 10))
    l2 = llamar(sesion, "draw_line", start_x=a[0], start_y=a[1], end_x=b[0], end_y=b[1])["entities"][-1]["id"]
    return l1, l2


def test_boc25_modelo_el_cuadrante_elige_45_o_135():
    b = Boceto()
    l1, l2 = b.agregar_linea((0, 0), (10, 0)), b.agregar_linea((10, 10), (0, 0))
    assert b.medir_cota("angulo", [l1, l2]) == pytest.approx(135)        # sin cuadrante: según cómo se dibujó
    agudo, obtuso = b.cuadrante_angulo(l1, l2, (5, 1)), b.cuadrante_angulo(l1, l2, (-5, 1))
    assert b.medir_cota("angulo", [l1, l2], cuadrante=agudo) == pytest.approx(45)
    assert b.medir_cota("angulo", [l1, l2], cuadrante=obtuso) == pytest.approx(135)
    b2 = Boceto()
    m1, m2 = b2.agregar_linea((0, 0), (10, 0)), b2.agregar_linea((0, 0), (10, 10))
    assert b2.medir_cota("angulo", [m1, m2], cuadrante=b2.cuadrante_angulo(m1, m2, (5, 1))) == pytest.approx(45)
    with pytest.raises(Exception, match="cuadrante"):
        b.agregar_cota("radio", [b.agregar_circulo((0, 0), 2)], "2", {"cuadrante": 1})


def test_boc25_api_near_mide_el_cuadrante_y_persiste(sesion):
    l1, l2 = _dos_lineas_45(sesion)
    sin = llamar(sesion, "add_dimension", sketch="Base", type="angle", entities=[l1, l2], reference=True)
    assert sin["dimension"]["value"] == pytest.approx(135) and "quadrant" not in sin["dimension"]
    k = llamar(sesion, "add_dimension", sketch="Base", type="angle", entities=[l1, l2], near=[5, 1])["dimension"]
    assert k["value"] == pytest.approx(45) and k["quadrant"] in (0, 1, 2, 3)
    receta = llamar(sesion, "get_recipe")
    llamar(sesion, "apply_recipe", recipe=receta)
    info = llamar(sesion, "get_sketch", sketch="Base")
    cota = next(d for d in info["dimensions"] if d["id"] == k["id"])
    assert (cota["quadrant"], cota["value"]) == (k["quadrant"], pytest.approx(45))
    r = api.llamar(sesion, "add_dimension", {"sketch": "Base", "type": "distance", "entities": [l1], "near": [1, 1]})
    assert not r["ok"] and r["error_kind"] == "INVALID_DIMENSION", r


def test_boc25_api_edit_dimension_cambia_el_cuadrante(sesion):
    l1, l2 = _dos_lineas_45(sesion)
    llamar(sesion, "add_constraint", sketch="Base", type="fix", entities=[l1])
    k = llamar(sesion, "add_dimension", sketch="Base", type="angle", entities=[l1, l2], value=30, near=[5, 1])
    assert k["dimension"]["value"] == pytest.approx(30)
    e = llamar(sesion, "edit_dimension", dimension=k["dimension"]["id"], near=[-5, 1])["dimension"]
    assert e["quadrant"] != k["dimension"]["quadrant"] and e["expression"] == k["dimension"]["expression"]
    info = llamar(sesion, "get_sketch", sketch="Base")
    assert info["status"] != "over_constrained"
    diag = next(c for c in info["entities"] if c["id"] == l2)
    (x1, y1), (x2, y2) = diag["start"], diag["end"]
    ang = math.degrees(math.atan2(abs(y2 - y1), abs(x2 - x1)))
    assert ang == pytest.approx(30, abs=0.01)                     # la recta sigue a 30°, del otro lado del cruce
    assert (x2 - x1) * (y2 - y1) < 0                               # ahora sube hacia la izquierda: 30° en ese cuadrante


def test_boc25_ui_el_clic_de_ubicacion_elige_el_cuadrante():
    from PySide6.QtCore import QPointF  # noqa: F401
    lz, linea = _lienzo_boc1()
    diagonal = lz.b.agregar_linea((10, 10), (0, 0))
    lz.resolver()
    clics = iter([linea, diagonal, None])
    lz.entidad_en = lambda _pos: next(clics)
    lz.set_herramienta("cota")
    lz._clic_cota(lz.a_px(20, 0))
    lz._clic_cota(lz.a_px(5, 5))
    assert lz.entrada is None and lz._esperando_ubicacion          # el ángulo espera el clic que lo ubica
    lz._pos_cursor = lz.a_px(-5, 1)
    assert lz.b.medir(lz._cota_viva()) == pytest.approx(135)        # la vista previa sigue al cursor
    lz._clic_cota(lz.a_px(5, 1))
    lz.entrada.aceptado.emit([""])
    cota = next(k for k in lz.b.cotas.values() if k.tipo == "angulo")
    assert lz.b.medir(cota) == pytest.approx(45) and "cuadrante" in cota.datos


def _esquina(sesion):
    l1 = llamar(sesion, "draw_line", start_x=0, start_y=0, end_x=20, end_y=0)["entities"][0]["id"]
    l2 = llamar(sesion, "draw_line", start_x=20, start_y=0, end_x=20, end_y=20)["entities"][-1]["id"]
    return l1, l2


def _cotas_chaflan(sesion, antes):
    return [d for d in llamar(sesion, "get_sketch", sketch="Base")["dimensions"] if d["id"] not in antes]


def test_boc25_chaflan_de_distancias_iguales_queda_ligado(sesion):
    l1, l2 = _esquina(sesion)
    antes = {d["id"] for d in llamar(sesion, "get_sketch", sketch="Base")["dimensions"]}
    llamar(sesion, "sketch_chamfer", line1=l1, line2=l2, distance=3)
    primera, segunda = _cotas_chaflan(sesion, antes)
    assert segunda["expression"] == primera["name"] and segunda["value"] == pytest.approx(3)
    llamar(sesion, "edit_dimension", dimension=primera["id"], value=5)
    primera, segunda = _cotas_chaflan(sesion, antes)
    assert (primera["value"], segunda["value"]) == (pytest.approx(5), pytest.approx(5))
    llamar(sesion, "delete_sketch_entities", sketch="Base", entities=[primera["id"]])    # borrar la 1.ª se puede
    (sola,) = _cotas_chaflan(sesion, antes)
    assert (sola["id"], sola["value"]) == (segunda["id"], pytest.approx(5))


def test_boc25_chaflan_de_dos_distancias_es_independiente(sesion):
    l1, l2 = _esquina(sesion)
    antes = {d["id"] for d in llamar(sesion, "get_sketch", sketch="Base")["dimensions"]}
    llamar(sesion, "sketch_chamfer", line1=l1, line2=l2, distance=3, distance2=4)
    primera, segunda = _cotas_chaflan(sesion, antes)
    llamar(sesion, "edit_dimension", dimension=primera["id"], value=5)
    primera, segunda = _cotas_chaflan(sesion, antes)
    assert (primera["value"], segunda["value"]) == (pytest.approx(5), pytest.approx(4))


# ---------------------------------------------------------------- BOC-7: conflictos en rojo, F5 y navegador
def _lienzo_en_conflicto():
    lz, linea = _lienzo_boc1()
    lz.b.agregar_cota("distancia_v", [linea], "5")            # una horizontal con alto 5: choca
    lz.resolver()
    return lz, linea


def test_boc7_ui_conflicto_en_rojo_y_f5_lista_lo_que_choca():
    from omnicad.ui.editor_boceto import CONFLICTO
    lz, linea = _lienzo_en_conflicto()
    assert not lz.resultado.ok
    horizontal = next(iter(lz.b.restricciones))
    cota = next(iter(lz.b.cotas))
    assert set(lz.conflictos) == {horizontal, cota}
    assert linea in lz.geometria_en_conflicto()
    assert lz._color_curva(lz.b.curvas[linea], set(), set(), lz.geometria_en_conflicto())[0] == CONFLICTO
    texto = lz.mostrar_conflictos()
    assert texto.startswith("Chocan:") and "horizontal" in texto and "distancia vertical" in texto
    lz.resize(400, 300)
    assert not lz.grab().isNull()                              # el dibujo en rojo no rompe el pintado
    lz.aplicar_cambio(lambda: lz.b.eliminar(cota))
    assert lz.resultado.ok and lz.conflictos == [] and lz.texto_conflictos() == ""
    assert lz.mostrar_conflictos() == "No hay restricciones ni cotas en conflicto."


def test_boc7_paleta_nombra_lo_que_choca():
    from omnicad.ui.modo_boceto import PaletaBoceto
    lz, _linea = _lienzo_en_conflicto()
    paleta = PaletaBoceto()
    paleta.set_estado(lz.resultado, lz.texto_conflictos())
    assert paleta.estado.text().startswith("⚠") and "Chocan:" in paleta.estado.text()


def test_boc7_navegador_candado_y_marca_roja_segun_el_solver():
    from omnicad.restricciones.solver import ResultadoSolver
    from omnicad.ui.navegador import ROL_ICONO, Navegador, estado_boceto
    _lienzo_boc1()                                             # QApplication
    ok0, ok2 = ResultadoSolver("ok", 0, 0.0), ResultadoSolver("ok", 2, 0.0)
    mal = ResultadoSolver("inconsistente", 0, 1.0)
    assert estado_boceto(ok0)[0] == "boceto_bloqueado" and estado_boceto(mal)[0] == "boceto_conflicto"
    assert estado_boceto(ok2) == ("boceto", "Boceto sub-restringido: faltan 2 grado(s) de libertad.")
    assert estado_boceto(None) == ("boceto", "")
    nav = Navegador()
    vis = {k: True for k in ("todo", "origen", "planos", "cuerpos", "bocetos", "calcomanias")}
    nav.actualizar("Doc", [], [("op1", "Boceto1", *estado_boceto(ok0))], set(), vis)
    it = nav.item("op1")
    assert it.data(0, ROL_ICONO) == "boceto_bloqueado" and it.toolTip(0) == "Boceto totalmente restringido."
    nav.marcar_boceto("op1", mal)                              # al editar: se actualiza en el lugar
    assert it.data(0, ROL_ICONO) == "boceto_conflicto" and "conflicto" in it.toolTip(0)


def test_boc7_api_browser_state_trae_status_y_dof(sesion):
    linea = llamar(sesion, "draw_line", start_x=0, start_y=0, end_x=10, end_y=0)["entities"][0]["id"]
    estado = llamar(sesion, "get_browser_state")["sketches"]
    dof = llamar(sesion, "get_sketch", sketch="Base")["dof"]
    assert [(s["name"], s["status"], s["dof"]) for s in estado] == [("Base", "under_constrained", dof)]
    llamar(sesion, "add_constraint", sketch="Base", type="horizontal", entities=[linea])
    op = next(o for o in sesion.doc.operaciones if isinstance(o, OpBoceto))
    nueva = op.copia()
    nueva.boceto.agregar_cota("distancia_v", [linea], "5")
    sesion.doc.reemplazar(op.id, nueva)
    estado = llamar(sesion, "get_browser_state")["sketches"][0]
    assert estado["status"] == "over_constrained"
    assert llamar(sesion, "get_sketch", sketch="Base")["conflicts"]


def test_boc2_apply_recipe_append_renombra_cotas_que_chocan_y_exportar_omite_dn(sesion, tmp_path):
    _rectangulo_boc2(sesion)
    llamar(sesion, "add_dimension", sketch="Base", type="radius", entities=[llamar(
        sesion, "draw_circle", radius=2, center_x=10, center_y=5)["entities"][0]["id"]], value="d2/5")
    receta = llamar(sesion, "get_recipe")["recipe"]
    llamar(sesion, "apply_recipe", recipe=receta, mode="append")
    cotas = {n: p for n, p in ((p["name"], p) for p in llamar(sesion, "get_parameters")["parameters"]) if "source" in p}
    assert len(cotas) == 6 and {p["sketch"] for p in cotas.values()} == {"op1", "op2"}
    nueva = next(p for p in cotas.values() if p["sketch"] == "op2" and p["expression"].startswith("d"))
    citada = nueva["expression"].split("/")[0]            # la copia cita SU d2, no el del boceto original
    assert cotas[citada]["sketch"] == "op2"
    csv = tmp_path / "p.csv"
    assert llamar(sesion, "export_parameters", path=str(csv))["count"] == 0
