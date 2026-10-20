"""Cotas y anotaciones del plano mediante la API pública, sin Qt."""
import inspect
import math
from copy import deepcopy

import pytest

from omnicad import api
from omnicad.api import herramientas_dibujo_notas as notas


def _ok(sesion, nombre, args=None):
    resultado = api.llamar(sesion, nombre, args or {})
    assert resultado["ok"], resultado
    return resultado["result"]


@pytest.fixture
def plano():
    sesion = api.Sesion()
    _ok(sesion, "create_box", {"length": 40, "width": 20, "height": 10, "name": "Caja"})
    base = _ok(sesion, "create_drawing", {"bodies": ["Caja"]})["views"][0]
    _ok(sesion, "edit_drawing_view", {"view": base["id"], "scale": 2})
    base = _ok(sesion, "get_drawing")["views"][0]
    x, y = base["position"]
    hija = _ok(sesion, "add_drawing_view", {"type": "projected", "parent": base["id"],
                                            "position": [x + 130, y]})
    return sesion, base, hija


def _esquinas(base):
    x0, y0, x1, y1 = base["bbox"]
    return [x0, y0], [x1, y0], [x1, y1], [x0, y1]


def test_catalogo_y_docstrings():
    funciones = {nombre: funcion for nombre, funcion in vars(notas).items()
                 if inspect.isfunction(funcion) and funcion.__module__ == notas.__name__ and not nombre.startswith("_")}
    assert len(funciones) == 11
    catalogo = {h["nombre"]: h for h in api.catalogo("dibujo")}
    for nombre, funcion in funciones.items():
        herramienta = catalogo[nombre]
        assert herramienta["modifica"] == (nombre != "get_drawing_geometry")
        parametros = list(inspect.signature(funcion).parameters)[1:]
        assert set(parametros) == set(herramienta["esquema"]["properties"])
        assert all(herramienta["esquema"]["properties"][p].get("description") for p in parametros)


@pytest.mark.parametrize("tipo,indices,valor", [
    ("horizontal", (0, 1), 40), ("vertical", (1, 2), 10),
    ("aligned", (0, 2), math.hypot(40, 10)),
    ("ordinate_x", (0, 2), 40), ("ordinate_y", (0, 2), 10),
])
def test_cotas_lineales_y_ordenadas(plano, tipo, indices, valor):
    sesion, base, _ = plano
    esquinas = _esquinas(base)
    puntos = [[coordenada + 0.2 for coordenada in esquinas[i]] for i in indices]
    cota = _ok(sesion, "add_drawing_dimension", {"view": base["id"], "type": tipo,
                                                "points": puntos, "place": [100, 120]})
    assert cota["value"] == pytest.approx(valor, abs=0.0001)
    assert cota["view"] == base["id"]


def test_geometria_limite_y_sin_enganche(plano):
    sesion, base, _ = plano
    geometria = _ok(sesion, "get_drawing_geometry", {"view": base["id"]})
    assert len(geometria["points"]) == 8
    assert len(geometria["segments"]) == 4
    assert geometria["circles"] == []
    assert all(list(p) in geometria["points"] for p in _esquinas(base))
    limitado = _ok(sesion, "get_drawing_geometry", {"view": base["id"], "limit": 1})
    assert len(limitado["points"]) == len(limitado["segments"]) == 1
    assert _ok(sesion, "get_drawing_geometry", {"view": base["id"], "limit": 0}) == {
        "points": [], "segments": [], "circles": []}
    a, b, _, _ = _esquinas(base)
    b[0] -= 1
    cota = _ok(sesion, "add_drawing_dimension", {"view": base["id"], "type": "horizontal",
                                                "points": [a, b], "place": [100, 120], "snap": False})
    assert cota["value"] == 39.5


def test_circulos_cotas_radiales_y_marca():
    sesion = api.Sesion()
    _ok(sesion, "create_cylinder", {"radius": 8, "height": 12, "name": "Cilindro"})
    _ok(sesion, "create_drawing", {"bodies": ["Cilindro"]})
    superior = _ok(sesion, "add_drawing_view", {"bodies": ["Cilindro"], "orientation": "top", "scale": 0.5})
    geometria = _ok(sesion, "get_drawing_geometry", {"view": superior["id"]})
    circulo = geometria["circles"][0]
    assert circulo["radius"] == 4 and circulo["full"] is True
    assert circulo["center"] == pytest.approx(superior["position"])
    x, y = circulo["center"]
    borde = [x + circulo["radius"], y]
    for tipo, valor in (("diameter", 16), ("radius", 8)):
        cota = _ok(sesion, "add_drawing_dimension", {"view": superior["id"], "type": tipo,
                                                    "points": [borde], "place": [x + 15, y + 15], "snap": False})
        assert cota["value"] == valor
    marca = _ok(sesion, "add_drawing_center_mark", {"view": superior["id"], "point": borde})
    assert marca["radius"] == 8 and marca["type"] == "marca_centro"


@pytest.mark.parametrize("explicitos", [False, True])
def test_cota_angular(plano, explicitos):
    sesion, base, _ = plano
    a, b, c, _ = _esquinas(base)
    puntos = [a, b, b, c] if explicitos else [[(a[0] + b[0]) / 2, a[1]], [b[0], (b[1] + c[1]) / 2]]
    cota = _ok(sesion, "add_drawing_dimension", {"view": base["id"], "type": "angle", "points": puntos,
                                                "place": [b[0] - 5, b[1] + 5]})
    assert cota["value"] == 90 and cota["text"] == "90°"


def test_texto_propio_edicion_y_deshacer(plano):
    sesion, base, _ = plano
    a, b, _, _ = _esquinas(base)
    cota = _ok(sesion, "add_drawing_dimension", {"view": base["id"], "type": "horizontal", "points": [a, b],
                                                "place": [100, 120], "text": "Ancho nominal"})
    assert cota["text"] == "Ancho nominal" and cota["value"] == 40
    cota = _ok(sesion, "edit_drawing_annotation", {"annotation": cota["id"], "text": ""})
    assert cota["text"] == "40" and cota["custom_text"] is None
    _ok(sesion, "undo")
    assert _ok(sesion, "get_drawing")["annotations"][0]["text"] == "Ancho nominal"
    _ok(sesion, "undo")
    assert _ok(sesion, "get_drawing")["annotations"] == []


def test_notas_textos_globos_tabla_y_linea(plano):
    sesion, base, _ = plano
    nota = _ok(sesion, "add_drawing_note", {"arrow": [10, 10], "position": [20, 30], "text": "Nota"})
    movida = _ok(sesion, "move_drawing_element", {"element": nota["id"], "delta": [7, -4]})
    assert movida["position"] == [27, 26] and movida["moved"] == [7, -4]
    assert movida["arrow"] == nota["arrow"]
    asociada = _ok(sesion, "add_drawing_note", {"arrow": base["position"], "position": [20, 30], "text": "Vista"})
    assert asociada["view"] == base["id"]
    texto = _ok(sesion, "add_drawing_text", {"position": [20, 40], "text": "Título"})
    assert texto["height"] == 3.5
    globo = _ok(sesion, "add_drawing_balloon", {"view": base["id"], "point": base["position"], "position": [80, 80]})
    assert globo["text"] == "1"
    for anotacion in (nota, texto, globo):
        editada = _ok(sesion, "edit_drawing_annotation", {"annotation": anotacion["id"], "text": "Nuevo"})
        assert editada["text"] == "Nuevo"
    tabla = _ok(sesion, "add_drawing_table", {"position": [20, 50]})
    assert tabla["position"] == [20, 50] and tabla["type"] == "tabla"
    assert _ok(sesion, "get_drawing")["parts_list"][1][2] == "Caja"
    a, b, _, _ = _esquinas(base)
    linea = _ok(sesion, "add_drawing_centerline", {"view": base["id"], "start": [a[0] + 0.2, a[1]], "end": b})
    assert linea["points"][1][0] - linea["points"][0][0] == 40
    assert _ok(sesion, "delete_drawing_element", {"element": tabla["id"]}) == {"deleted": [tabla["id"]]}


def test_mover_alineada_y_borrado_en_cascada(plano):
    sesion, base, hija = plano
    movida = _ok(sesion, "move_drawing_element", {"element": hija["id"], "delta": [12, 23]})
    assert movida["moved"] == [12, 0]
    assert movida["position"] == pytest.approx([hija["position"][0] + 12, hija["position"][1]])
    ids = {base["id"], hija["id"]}
    for v in (base, hija):
        nota = _ok(sesion, "add_drawing_note", {"view": v["id"], "arrow": v["position"],
                                                "position": [20, 30], "text": "Asociada"})
        ids.add(nota["id"])
    borrado = _ok(sesion, "delete_drawing_element", {"element": base["id"]})
    assert set(borrado["deleted"]) == ids
    dibujo = _ok(sesion, "get_drawing")
    assert dibujo["views"] == dibujo["annotations"] == []


def test_errores_y_atomicidad(plano):
    sesion, base, _ = plano
    a, b, _, _ = _esquinas(base)
    argumentos = {"view": base["id"], "type": "horizontal", "points": [a, b], "place": [100, 120]}
    casos = [
        ("add_drawing_dimension", {**argumentos, "type": "inventada"}, "INVALID_ARGUMENTS"),
        ("add_drawing_dimension", {**argumentos, "points": [[1], b]}, "INVALID_ARGUMENTS"),
        ("add_drawing_dimension", {**argumentos, "points": [a]}, "INVALID_ARGUMENTS"),
        ("add_drawing_dimension", {**argumentos, "view": "v999"}, "DRAWING_ELEMENT_NOT_FOUND"),
        ("add_drawing_dimension", {**argumentos, "type": "radius", "points": [a]}, "INVALID_ARGUMENTS"),
        ("add_drawing_dimension", {**argumentos, "type": "angle", "points": [[0, 0], [1, 0]]}, "INVALID_ARGUMENTS"),
        ("add_drawing_dimension", {**argumentos, "type": "angle", "points": [a, b, a, b]}, "OPERATION_FAILED"),
        ("get_drawing_geometry", {"view": base["id"], "limit": -1}, "INVALID_ARGUMENTS"),
        ("move_drawing_element", {"element": base["id"], "delta": [float("nan"), 0]}, "INVALID_ARGUMENTS"),
        ("delete_drawing_element", {"element": "a999"}, "DRAWING_ELEMENT_NOT_FOUND"),
        ("edit_drawing_annotation", {"annotation": base["id"], "text": "X"}, "INVALID_ARGUMENTS"),
        ("add_drawing_text", {"position": [1, 2], "text": " "}, "INVALID_ARGUMENTS"),
        ("add_drawing_text", {"position": [1, 2], "text": "X", "height": -1}, "INVALID_ARGUMENTS"),
    ]
    antes = deepcopy(sesion.doc.espacios["dibujo"])
    for nombre, args, tipo in casos:
        resultado = api.llamar(sesion, nombre, args)
        assert not resultado["ok"] and resultado["error_kind"] == tipo, resultado
        assert sesion.doc.espacios["dibujo"] == antes


def test_enganche_se_limita_a_la_vista_pedida(plano):
    sesion, base, _ = plano
    # La segunda base se superpone: la primera tiene vértices 1 mm más cerca de los puntos consultados.
    segunda = _ok(sesion, "add_drawing_view", {"bodies": ["Caja"], "position": base["position"], "scale": 2})
    _ok(sesion, "move_drawing_element", {"element": segunda["id"], "delta": [1, 0]})
    a, b, _, _ = _esquinas(base)
    cota = _ok(sesion, "add_drawing_dimension", {"view": segunda["id"], "type": "horizontal", "points": [a, b],
                                                "place": [100, 120]})
    assert cota["value"] == 40 and cota["points"][0][0] == -20
