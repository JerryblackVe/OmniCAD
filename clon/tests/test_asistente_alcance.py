"""IA-11: todas las herramientas del catálogo al alcance del chat, en pocas llamadas y sin mandar 340 esquemas.

Modo API: `buscar_herramientas` + usar (2 llamadas). Modo suscripción: `call_tool` del `omnicad-mcp --meta-tools`.
Los tokens se estiman como largo / 4 (la regla del plan; sin red ni tokenizador)."""
import asyncio
import json

import pytest

from omnicad import api
from omnicad.asistente import bucle, prompt
from omnicad.asistente.herramientas import MODOS, NUCLEO, TOPE_BUSQUEDA, TOPE_RESULTADO, Herramientas
from omnicad.asistente.proveedores.base import PedidoHerramienta, ProveedorFalso, Respuesta
from omnicad.servidor_mcp.servidor import CALL_TOOL, FIND_TOOLS, crear_servidor

TOPE_TOKENS = 25_000
CATALOGO = {h["nombre"]: h for h in api.catalogo()}
PROHIBIDAS = ["execute_code", "assistant_ask", next(h["nombre"] for h in api.catalogo("dev")), "no_existe",
              "call_tool", "find_tools"]


def tokens(*partes):
    return sum(len(p if isinstance(p, str) else json.dumps(p, ensure_ascii=False)) for p in partes) // 4


def test_modo_api_cada_herramienta_en_dos_llamadas():
    alcanzables = Herramientas().catalogo
    assert len(alcanzables) > 300
    for nombre in alcanzables:
        h = Herramientas()
        assert h.buscar(nombres=[nombre])["ok"], nombre          # llamada 1: buscar
        assert h.permitida(nombre) and nombre in [d["nombre"] for d in h.definiciones()]   # llamada 2: usarla
    for nombre in PROHIBIDAS:
        r = Herramientas().buscar(nombres=[nombre])
        assert r["error_kind"] == "TOOL_NOT_AVAILABLE", nombre


def test_modo_api_de_punta_a_punta_con_una_fuera_del_nucleo():
    sesion = api.Sesion()
    api.llamar(sesion, "create_box", {"length": 10, "width": 10, "height": 10})
    cuerpo = api.llamar(sesion, "get_scene_info", {})["result"]["bodies"][0]["id"]
    proveedor = ProveedorFalso([
        Respuesta(herramientas=[PedidoHerramienta("b", "buscar_herramientas", {"nombres": ["set_appearance"]})]),
        Respuesta(herramientas=[PedidoHerramienta("a", "set_appearance", {"bodies": [cuerpo], "color": "#ff0000"})]),
        Respuesta(texto="Pintada."),
    ])
    llamadas = []

    def ejecutar(nombre, args):
        llamadas.append(nombre)
        return api.llamar(sesion, nombre, args)

    assert bucle.correr(proveedor, [], ejecutar)["motivo"] == "fin"
    resultado = json.loads(proveedor.recibidos[2][0][-1]["contenido"][0]["contenido"][0]["texto"])
    assert llamadas == ["set_appearance"] and resultado["ok"], resultado


def _servidor(despachados):
    servidor = crear_servidor(modo="sin_ventana", meta=True, herramientas=[])
    servidor.despachar = lambda nombre, args: despachados.append((nombre, args)) or {"ok": True, "result": {},
                                                                                     "avisos": []}
    return servidor


def _llamar(servidor, nombre, args):
    resultado = asyncio.run(servidor.call_tool(nombre, args))
    return json.loads(resultado.content[0].text), resultado.is_error


def test_modo_suscripcion_cada_herramienta_por_call_tool_con_su_nombre_real():
    despachados = []
    servidor = _servidor(despachados)
    try:
        assert {t.name for t in asyncio.run(servidor.list_tools())} == {"find_tools", "call_tool"}

        async def todas():
            for nombre in Herramientas().catalogo:
                r = await servidor.call_tool("call_tool", {"name": nombre, "args": {"x": 1}})
                assert not r.is_error, nombre
        asyncio.run(todas())
        assert despachados == [(n, {"x": 1}) for n in Herramientas().catalogo]
        despachados.clear()
        for nombre in PROHIBIDAS:
            respuesta, es_error = _llamar(servidor, "call_tool", {"name": nombre})
            assert es_error and respuesta["error_kind"] == "TOOL_NOT_AVAILABLE", nombre
        for malos in ([1], [], ""):
            respuesta, es_error = _llamar(servidor, "call_tool", {"name": "create_box", "args": malos})
            assert es_error and respuesta["error_kind"] == "INVALID_ARGUMENTS", malos
        assert despachados == []
        # find_tools da el esquema original, listo para call_tool
        respuesta, _ = _llamar(servidor, "find_tools", {"names": ["set_appearance", "execute_code"]})
        assert [t["name"] for t in respuesta["result"]["tools"]] == ["set_appearance"]
        assert respuesta["result"]["tools"][0]["input_schema"] == CATALOGO["set_appearance"]["esquema"]
        assert respuesta["result"]["unknown"] == ["execute_code"]
        respuesta, _ = _llamar(servidor, "find_tools", {"query": "aspecto color"})
        assert "set_appearance" in [t["name"] for t in respuesta["result"]["tools"]]
        respuesta, es_error = _llamar(servidor, "find_tools", {})
        assert es_error and respuesta["error_kind"] == "INVALID_ARGUMENTS"
    finally:
        servidor.cerrar()


def test_sin_meta_tools_no_hay_find_ni_call():
    servidor = crear_servidor(modo="sin_ventana", herramientas=["get_timeline"])
    try:
        assert {t.name for t in asyncio.run(servidor.list_tools())} == {"get_timeline"}
        respuesta, es_error = _llamar(servidor, "call_tool", {"name": "create_box"})
        assert es_error and respuesta["error_kind"] == "UNKNOWN_TOOL"
    finally:
        servidor.cerrar()


@pytest.mark.parametrize("modo", MODOS)
def test_tokens_por_paso_en_todos_los_modos(modo):
    sistema = prompt.armar_sistema(api.Sesion(), modo)
    h = Herramientas(modo=modo)
    # modo API, el peor caso de una búsqueda: las TOPE_BUSQUEDA de esquema más largo que no están en el núcleo
    pesadas = sorted((n for n in h.catalogo if n not in NUCLEO), key=lambda n: -len(json.dumps(h.catalogo[n]["esquema"])))
    assert h.buscar(nombres=pesadas[:TOPE_BUSQUEDA])["ok"]
    assert tokens(sistema, h.definiciones()) <= TOPE_TOKENS
    # modo suscripción: la lista corta del CLI más find_tools y call_tool
    cli = [CATALOGO[n] for n in h.para_cli()] + [FIND_TOOLS, CALL_TOOL]
    assert tokens(sistema, [{k: d[k] for k in ("nombre", "descripcion", "esquema")} for d in cli]) <= TOPE_TOKENS
    # contra mandar todo el catálogo, que era lo único que alcanzaba todas
    assert tokens(list(Herramientas().catalogo.values())) > 4 * TOPE_TOKENS


def test_resultados_largos_se_recortan_para_el_modelo_pero_no_en_el_panel():
    enorme = {"ok": True, "result": {"texto": "x" * 50_000}, "avisos": []}
    proveedor = ProveedorFalso([Respuesta(herramientas=[PedidoHerramienta("1", "get_timeline", {})]),
                                Respuesta(texto="ok")])
    eventos = []
    bucle.correr(proveedor, [], lambda n, a: enorme, al_evento=lambda t, d: eventos.append((t, d)))
    texto = proveedor.recibidos[1][0][-1]["contenido"][0]["contenido"][0]["texto"]
    assert len(texto) < TOPE_RESULTADO + 200 and "resultado recortado" in texto
    assert next(d for t, d in eventos if t == "herramienta")["respuesta"] == enorme
    servidor = crear_servidor(modo="sin_ventana", meta=True, herramientas=["get_timeline"])
    servidor.despachar = lambda nombre, args: enorme
    try:
        texto = asyncio.run(servidor.call_tool("get_timeline", {})).content[0].text
        assert len(texto) < TOPE_RESULTADO + 200 and "resultado recortado" in texto
    finally:
        servidor.cerrar()


def test_prompt_lleva_el_indice_de_todo_lo_alcanzable():
    sistema = prompt.armar_sistema(api.Sesion(), "hacer")
    assert Herramientas().indice() in sistema
    assert "call_tool" in sistema and "buscar_herramientas" in sistema
