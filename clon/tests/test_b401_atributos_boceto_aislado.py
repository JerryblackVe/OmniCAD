"""B-401: el cálculo aislado conserva los efectos del boceto igual que el cálculo local."""
import pytest

from omnicad import api
from omnicad.nucleo import aislado, geometria as geo
from omnicad.timeline.calculo_aislado import _codificar, _decodificar, _empaquetar
from omnicad.timeline.operaciones import OpBoceto


def llamar(sesion, nombre, **argumentos):
    respuesta = api.llamar(sesion, nombre, argumentos)
    assert respuesta["ok"], respuesta
    return respuesta["result"]


def _pieza(atributo):
    s = api.Sesion()
    if atributo == "perdidas":
        llamar(s, "create_sketch", name="Perfil", plane="XY")
        for radio in (40, 20):
            llamar(s, "draw_arc", start_x=radio, start_y=0, mid_x=0, mid_y=radio, end_x=-radio, end_y=0)
        for inicio, fin in ((-40, -20), (20, 40)):
            llamar(s, "draw_line", start_x=inicio, start_y=0, end_x=fin, end_y=0)
        llamar(s, "extrude", sketch="Perfil", profile=0, distance=10)
        llamar(s, "create_sketch", name="Boceto", plane=">Z", project_edges=True)
        entidades = llamar(s, "get_sketch", sketch="Perfil")["entities"]
        arco = next(e["id"] for e in entidades if e["type"] == "arc")
        linea = next(e["id"] for e in entidades if e["type"] == "line")
        llamar(s, "sketch_fillet", sketch="Perfil", entity1=linea, entity2=arco, radius=2)
    else:
        llamar(s, "create_box", length=20, width=20, height=20)
        llamar(s, "create_sketch", name="Boceto", plane="XZ")
        if atributo == "rehechas":
            llamar(s, "project_to_sketch", bodies=["Cuerpo1"])
            arista = llamar(s, "find_edges", selector=">Z and |Y")["edges"][0]["id"]
            llamar(s, "fillet", edges=[arista], radius=2)
            llamar(s, "move_feature", feature="op3", index=1)
        else:
            llamar(s, "create_parameter", name="ancho", expression="20 mm")
            llamar(s, "add_text", text="{ancho}", font="Arial")
    assert llamar(s, "recompute_all")["failed_steps"] == []
    assert getattr(s.paso("Boceto"), atributo), atributo
    return s


@pytest.mark.parametrize("trabajador", [False, True], ids=["hijo_suelto", "trabajador"])
@pytest.mark.parametrize("atributo", ["rehechas", "perdidas", "_textos_parametricos"])
def test_misma_pieza_y_atributos_por_api(monkeypatch, trabajador, atributo):
    monkeypatch.setattr(aislado, "UMBRAL_COSTO_AISLAR_S", float("inf"))
    local = _pieza(atributo)
    receta = llamar(local, "get_recipe")
    medidas = llamar(local, "get_physical_properties")["bodies"]
    esperado = llamar(local, "get_sketch", sketch="Boceto")
    efectos = tuple(getattr(local.paso("Boceto"), k) for k in ("rehechas", "perdidas", "_textos_parametricos"))
    monkeypatch.setattr(aislado, "TRABAJADOR", trabajador)
    monkeypatch.setattr(aislado, "UMBRAL_PREVUELO_PARAMETROS", 1)

    def no_calcular(*args):
        raise AssertionError("El padre volvió a calcular el boceto")

    monkeypatch.setattr(OpBoceto, "ejecutar", no_calcular)
    otra = api.Sesion()
    llamar(otra, "apply_recipe", recipe=receta)
    # La segunda respuesta del trabajador reutiliza objetos; también debe conservar los efectos.
    for _ in range(2):
        recibidas = llamar(otra, "get_physical_properties")["bodies"]
        for antes, despues in zip(medidas, recibidas, strict=True):
            assert despues["volume"] == pytest.approx(antes["volume"], rel=1e-9)
            for limite in ("min", "max"):
                assert despues["bounding_box"][limite] == pytest.approx(antes["bounding_box"][limite], abs=1e-6)
        assert all(geo.es_valida(c.forma) for c in otra.doc.estado_final.cuerpos.values())
        assert tuple(getattr(otra.paso("Boceto"), k) for k in ("rehechas", "perdidas", "_textos_parametricos")) == efectos
        assert llamar(otra, "get_sketch", sketch="Boceto") == esperado
        assert llamar(otra, "recompute_all")["failed_steps"] == []
    if atributo == "rehechas":
        curva = next(e["id"] for e in esperado["entities"] if e["type"] == "arc")
        llamar(otra, "add_constraint", sketch="Boceto", type="fix", entities=[curva])
    elif atributo == "perdidas":
        llamar(otra, "manage_lost_projections", sketch="Boceto", action="break")
        assert not llamar(otra, "get_sketch", sketch="Boceto").get("projections")


@pytest.mark.parametrize("atributo", ["rehechas", "_textos_parametricos"])
def test_boceto_lento_va_al_hijo_por_costo(monkeypatch, atributo):
    monkeypatch.setattr(aislado, "UMBRAL_COSTO_AISLAR_S", float("inf"))
    s = _pieza(atributo)
    monkeypatch.setattr(aislado, "UMBRAL_COSTO_AISLAR_S", 0.5)
    s.doc._duraciones = [4.0] * len(s.doc.operaciones)
    assert len(s.doc.operaciones) < aislado.UMBRAL_PREVUELO_PARAMETROS
    assert s.doc._prevuelo_corresponde()

    def no_calcular(*args):
        raise AssertionError("El boceto lento se calculó en el padre")

    monkeypatch.setattr(OpBoceto, "ejecutar", no_calcular)
    assert llamar(s, "recompute_all")["failed_steps"] == []


@pytest.mark.parametrize("efectos", [None, ({}, []), ({}, {}, {}), ({"x": ([], [])}, [], {}), ({1: ([], [], [])}, [], {}), ({1: [[], []]}, [], {})])
def test_respuesta_con_atributos_invalidos_no_altera_la_pieza(monkeypatch, efectos):
    monkeypatch.setattr(aislado, "UMBRAL_COSTO_AISLAR_S", float("inf"))
    s = _pieza("_textos_parametricos")
    receta = llamar(s, "get_recipe")
    estado, texto = s.doc.estado_final, dict(s.paso("Boceto")._textos_parametricos)
    salida = _empaquetar(s.doc)
    datos = _decodificar(salida["calculo"])
    datos["efectos_boceto"][s.doc.indice(s.paso("Boceto").id)] = efectos
    salida["calculo"] = _codificar(datos, transporte=False)
    monkeypatch.setattr(aislado, "correr_json", lambda *args: salida)
    monkeypatch.setattr(aislado, "UMBRAL_PREVUELO_PARAMETROS", 1)
    respuesta = api.llamar(s, "recompute_all", {})
    assert not respuesta["ok"] and "atributos de boceto inválidos" in respuesta["mensaje"]
    assert llamar(s, "get_recipe") == receta
    assert s.doc.estado_final is estado
    assert s.paso("Boceto")._textos_parametricos == texto
