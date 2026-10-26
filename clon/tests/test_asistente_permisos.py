"""Permisos del asistente (IA-5) sin Qt: aprobación de tandas en el bucle y marca de deshacer del pedido."""
import json

import pytest

from omnicad import api
from omnicad.asistente import bucle, marca
from omnicad.asistente.herramientas import Herramientas
from omnicad.asistente.proveedores.base import PedidoHerramienta, ProveedorFalso, Respuesta


def caja(i, largo=10):
    return PedidoHerramienta(f"c{i}", "create_box", {"length": largo, "width": 10, "height": 10})


@pytest.fixture
def sesion():
    return api.Sesion()


def correr(sesion, guion, modo, respuestas_aprobar=(), cancelado=None, permisos="una_vez"):
    """Corre el bucle anotando cada tanda que se pide aprobar; responde con `respuestas_aprobar` (True por defecto)."""
    pedidas, respuestas = [], list(respuestas_aprobar)

    def aprobar(pedidos):
        pedidas.append([p.nombre for p in pedidos])
        return respuestas.pop(0) if respuestas else True

    proveedor = ProveedorFalso(guion)
    herramientas = Herramientas(modo=modo, permisos=permisos, ruta_doc=lambda: sesion.doc.ruta)
    resultado = bucle.correr(proveedor, [], lambda n, a: api.llamar(sesion, n, a), herramientas,
                             aprobar=aprobar, cancelado=cancelado)
    return resultado, pedidas, proveedor


def test_hacer_aprueba_una_vez_y_corre_todo(sesion):
    guion = [Respuesta(herramientas=[caja(1)]), Respuesta(herramientas=[caja(2)]),
             Respuesta(herramientas=[caja(3)]), Respuesta(texto="listo")]
    resultado, pedidas, _ = correr(sesion, guion, "hacer")
    assert resultado["motivo"] == "fin"
    assert pedidas == [["create_box"]]
    assert len(sesion.doc.estado_final.cuerpos) == 3


@pytest.mark.parametrize("modo", ["guiar", "hacer"])
def test_cada_paso_pide_en_cada_tanda_que_cambia(sesion, modo):
    guion = [Respuesta(herramientas=[caja(1)]), Respuesta(herramientas=[PedidoHerramienta("t", "get_timeline", {})]),
             Respuesta(herramientas=[caja(2), PedidoHerramienta("s", "get_scene_info", {})]), Respuesta(texto="ok")]
    resultado, pedidas, _ = correr(sesion, guion, modo, permisos="cada_paso")
    assert resultado["motivo"] == "fin"
    assert pedidas == [["create_box"], ["create_box"]]   # la tanda de solo lectura no pregunta; se muestran solo los cambios
    assert len(sesion.doc.estado_final.cuerpos) == 2


def test_una_vez_tambien_en_guiar(sesion):
    """Los permisos dicen CUÁNDO pregunta; el modo, QUÉ puede hacer (IA-15)."""
    guion = [Respuesta(herramientas=[caja(1)]), Respuesta(herramientas=[caja(2)]), Respuesta(texto="ok")]
    _, pedidas, _ = correr(sesion, guion, "guiar", permisos="una_vez")
    assert pedidas == [["create_box"]] and len(sesion.doc.estado_final.cuerpos) == 2


def test_nunca_no_pide_y_cambia_el_documento(sesion):
    guion = [Respuesta(herramientas=[caja(1)]), Respuesta(herramientas=[caja(2)]), Respuesta(texto="ok")]
    resultado, pedidas, _ = correr(sesion, guion, "hacer", permisos="nunca")
    assert resultado["motivo"] == "fin" and pedidas == []
    assert len(sesion.doc.estado_final.cuerpos) == 2


@pytest.mark.parametrize("permisos", ["nunca", "una_vez"])
def test_pisar_un_archivo_existente_pregunta_siempre(sesion, tmp_path, permisos):
    ruta = tmp_path / "pieza.omnicad"
    assert api.llamar(sesion, "create_box", {"length": 5, "width": 5, "height": 5})["ok"]
    assert api.llamar(sesion, "save_document", {"path": str(ruta)})["ok"]
    stl = tmp_path / "pieza.stl"
    stl.write_bytes(b"solid x\nendsolid x\n")
    guion = [Respuesta(herramientas=[caja(1)]),
             Respuesta(herramientas=[PedidoHerramienta("g", "save_document", {})]),        # encima del actual
             Respuesta(herramientas=[PedidoHerramienta("n", "save_document", {"path": str(tmp_path / "otra")})]),
             Respuesta(herramientas=[PedidoHerramienta("e", "export", {"path": str(stl), "overwrite": True})]),
             Respuesta(texto="ok")]
    resultado, pedidas, _ = correr(sesion, guion, "hacer", permisos=permisos)
    assert resultado["motivo"] == "fin"
    # nunca: solo los que pisan; una_vez: el plan (la caja) y después igual los que pisan. Un archivo nuevo no pregunta.
    assert pedidas == ([] if permisos == "nunca" else [["create_box"]]) + [["save_document"], ["export"]]
    assert (tmp_path / "otra.omnicad").exists()


def test_rechazar_pisar_el_archivo_en_nunca_no_lo_toca(sesion, tmp_path):
    ruta = tmp_path / "pieza.omnicad"
    assert api.llamar(sesion, "save_document", {"path": str(ruta)})["ok"]
    antes = ruta.read_bytes()
    guion = [Respuesta(herramientas=[caja(1)]), Respuesta(herramientas=[PedidoHerramienta("g", "save_document", {})]),
             Respuesta(texto="no")]
    resultado, pedidas, _ = correr(sesion, guion, "hacer", [False], permisos="nunca")
    assert resultado["motivo"] == "rechazado" and pedidas == [["save_document"]]
    assert ruta.read_bytes() == antes and len(sesion.doc.estado_final.cuerpos) == 1   # la caja sí, sin preguntar


@pytest.mark.parametrize("nombre", ["execute_code", "assistant_ask"])
def test_nunca_sigue_bloqueando_execute_code_y_el_grupo_asistente(sesion, nombre):
    guion = [Respuesta(herramientas=[PedidoHerramienta("x", nombre, {"code": "1", "prompt": "hola"})]),
             Respuesta(texto="ok")]
    mensajes = []
    proveedor = ProveedorFalso(guion)
    bucle.correr(proveedor, mensajes, lambda n, a: api.llamar(sesion, n, a),
                 Herramientas(modo="hacer", permisos="nunca"), aprobar=lambda pedidos: pytest.fail("no pregunta"))
    texto = json.loads(mensajes[1]["contenido"][0]["contenido"][0]["texto"])
    assert texto["error_kind"] == "TOOL_NOT_AVAILABLE" and not sesion.doc.operaciones


def test_permisos_invalidos():
    with pytest.raises(ValueError):
        Herramientas(permisos="a_veces")


@pytest.mark.parametrize("modo", ["explicar", "mostrar"])
def test_modos_que_no_cambian_nunca_piden(sesion, modo):
    guion = [Respuesta(herramientas=[PedidoHerramienta("v", "set_view", {"view": "top"}),
                                     PedidoHerramienta("t", "get_timeline", {})]), Respuesta(texto="ok")]
    _, pedidas, _ = correr(sesion, guion, modo)
    assert pedidas == []


@pytest.mark.parametrize("modo", ["hacer", "guiar"])
def test_rechazar_no_cambia_el_documento_y_avisa_al_modelo(sesion, modo):
    antes = json.dumps(sesion.doc.a_dict())
    guion = [Respuesta(herramientas=[PedidoHerramienta("t", "get_timeline", {}), caja(1)]), Respuesta(texto="no")]
    resultado, pedidas, proveedor = correr(sesion, guion, modo, [False])
    assert resultado["motivo"] == "rechazado" and pedidas == [["create_box"]]
    assert json.dumps(sesion.doc.a_dict()) == antes
    assert len(proveedor.recibidos) == 1           # no vuelve a preguntarle al modelo


def test_rechazar_deja_resultados_cancelled(sesion):
    mensajes = []
    proveedor = ProveedorFalso([Respuesta(herramientas=[PedidoHerramienta("t", "get_timeline", {}), caja(1)])])
    resultado = bucle.correr(proveedor, mensajes, lambda n, a: api.llamar(sesion, n, a), Herramientas(modo="hacer"),
                             aprobar=lambda pedidos: False)
    assert resultado["motivo"] == "rechazado"
    bloques = mensajes[-1]["contenido"]
    assert [b["id"] for b in bloques] == ["t", "c1"] and all(b["error"] for b in bloques)
    textos = [json.loads(b["contenido"][0]["texto"]) for b in bloques]
    assert {t["error_kind"] for t in textos} == {"CANCELLED"} and "no aprobó" in textos[0]["mensaje"]


def test_guiar_rechazar_la_segunda_tanda_conserva_la_primera(sesion):
    guion = [Respuesta(herramientas=[caja(1)]), Respuesta(herramientas=[caja(2)]), Respuesta(texto="x")]
    resultado, pedidas, _ = correr(sesion, guion, "guiar", [True, False], permisos="cada_paso")
    assert resultado["motivo"] == "rechazado" and len(pedidas) == 2
    assert len(sesion.doc.estado_final.cuerpos) == 1


def test_cancelar_mientras_espera_la_aprobacion_es_cancelado(sesion):
    estado = {"cancelado": False}

    def aprobar(pedidos):
        estado["cancelado"] = True               # la persona apretó Cancelar del pedido con la tarjeta abierta
        return False

    proveedor = ProveedorFalso([Respuesta(herramientas=[caja(1)])])
    resultado = bucle.correr(proveedor, [], lambda n, a: api.llamar(sesion, n, a), Herramientas(modo="hacer"),
                             aprobar=aprobar, cancelado=lambda: estado["cancelado"])
    assert resultado["motivo"] == "cancelado"
    assert not sesion.doc.operaciones


def test_sin_aprobar_corre_como_antes(sesion):
    proveedor = ProveedorFalso([Respuesta(herramientas=[caja(1)]), Respuesta(texto="ok")])
    assert bucle.correr(proveedor, [], lambda n, a: api.llamar(sesion, n, a))["motivo"] == "fin"
    assert len(sesion.doc.estado_final.cuerpos) == 1


def test_necesita_aprobacion_usa_la_regla_de_modos():
    h = Herramientas(modo="hacer")
    assert h.necesita_aprobacion("create_box") and h.necesita_aprobacion("save_document")
    assert not h.necesita_aprobacion("get_timeline") and not h.necesita_aprobacion("set_view")
    assert not h.necesita_aprobacion("buscar_herramientas")
    assert not Herramientas(modo="explicar").necesita_aprobacion("create_box")


def test_marca_vuelve_exactamente_al_documento_de_antes(sesion):
    api.llamar(sesion, "create_box", {"length": 10, "width": 10, "height": 10})
    doc = sesion.doc
    m = marca.tomar(doc)
    receta, pila = json.dumps(doc.a_dict()), list(doc._deshacer)
    volumen = api.llamar(sesion, "get_physical_properties", {})["result"]["total"]["volume"]
    assert not marca.cambio(m, doc)
    for paso in ({"length": 20, "width": 5, "height": 5}, {"length": 3, "width": 3, "height": 3}):
        api.llamar(sesion, "create_box", paso)
    doc.vistas["mia"] = {"x": 1}
    doc.unidades = {**doc.unidades, "longitud": "in"}
    assert marca.cambio(m, doc)
    marca.volver(m)
    assert json.dumps(doc.a_dict()) == receta and doc._deshacer == pila and not marca.cambio(m, doc)
    assert api.llamar(sesion, "get_physical_properties", {})["result"]["total"]["volume"] == pytest.approx(volumen)
    assert len(doc.estado_final.cuerpos) == 1


def test_marca_de_otro_documento_cuenta_como_cambio(sesion):
    m = marca.tomar(sesion.doc)
    api.llamar(sesion, "new_document", {})
    assert marca.cambio(m, sesion.doc)
