# -*- coding: utf-8 -*-
"""Servidor MCP: cliente en memoria del SDK, stdio REAL (subproceso) y HTTP local REAL."""
import asyncio
import base64
import json
import re
import socket
import struct
import subprocess
import sys
import time
from pathlib import Path

import pytest
from mcp.client import Client
from mcp.client.stdio import StdioServerParameters
from mcp.shared.exceptions import MCPError

from omnicad import VERSION, api
from omnicad.ejemplo import crear_documento_ejemplo
from omnicad.servidor_mcp import crear_servidor, main, textos
from omnicad.servidor_mcp.servidor import GRUPOS_POR_DEFECTO

RAIZ = Path(__file__).resolve().parent.parent          # carpeta `clon`
FIRMA_PNG = b"\x89PNG\r\n\x1a\n"
LIMITE_E2E = 90                                         # segundos: nada de procesos colgados


def correr(coro):
    return asyncio.run(asyncio.wait_for(coro, LIMITE_E2E))


def memoria(sesion=None, **kwargs):
    """Servidor armado sobre la sesión dada (por defecto, una con el ejemplo cargado)."""
    return crear_servidor(sesion or api.Sesion(crear_documento_ejemplo()), **kwargs)


def json_de(resultado):
    return json.loads(resultado.content[0].text)


def parametros_stdio(*args):
    # --modo sin_ventana: determinista aunque haya un OmniCAD abierto con el puente encendido en esta PC.
    return StdioServerParameters(command=sys.executable, args=["-m", "omnicad.servidor_mcp", "--modo", "sin_ventana", *args],
                                 cwd=str(RAIZ),
                                 env={"PYTHONPATH": str(RAIZ)})


# ---------------------------------------------------------------- herramientas
def test_list_tools_devuelve_todo_el_catalogo_con_sus_esquemas_exactos():
    async def caso():
        async with Client(memoria()) as c:
            return (await c.list_tools()).tools
    herramientas = correr(caso())
    catalogo = api.catalogo(GRUPOS_POR_DEFECTO)                # `dev` solo con --dev
    assert len(catalogo) >= 30 and [t.name for t in herramientas] == [h["nombre"] for h in catalogo]
    for t, h in zip(herramientas, catalogo, strict=True):
        assert t.input_schema == json.loads(json.dumps(h["esquema"])), t.name      # IGUAL al del catálogo
        assert t.description == h["descripcion"]
        assert t.annotations.read_only_hint is (not h["modifica"])


def test_create_parameter_y_get_parameters():
    async def caso():
        async with Client(memoria(api.Sesion())) as c:
            creado = await c.call_tool("create_parameter", {"name": "ancho", "expression": "60 mm"})
            lista = await c.call_tool("get_parameters", {})
            return creado, lista
    creado, lista = correr(caso())
    assert not creado.is_error and json_de(creado)["result"]["value"] == 60.0
    assert [p["name"] for p in json_de(lista)["result"]["parameters"]] == ["ancho"]
    assert lista.structured_content is None                       # el JSON va una sola vez (en el texto)


def test_imagen_del_viewport_es_contenido_de_imagen_png_valido():
    async def caso():
        async with Client(memoria()) as c:
            return await c.call_tool("get_viewport_image", {"view": "iso", "width": 320, "height": 240})
    r = correr(caso())
    assert not r.is_error and [x.type for x in r.content] == ["text", "image"]
    imagen = r.content[1]
    png = base64.b64decode(imagen.data)
    assert imagen.mime_type == "image/png" and png[:8] == FIRMA_PNG
    assert struct.unpack(">II", png[16:24]) == (320, 240)
    texto = r.content[0].text
    assert imagen.data not in texto and len(texto) < 1500          # en el JSON queda solo la referencia
    referencia = json.loads(texto)["result"]["image"]
    assert referencia == {"attached_image": 1, "mime_type": "image/png", "width": 320, "height": 240}


def test_los_errores_vuelven_con_is_error_y_error_kind():
    async def caso():
        async with Client(memoria()) as c:
            return [await c.call_tool("set_parameter", {"name": "no_existe", "expression": "1"}),
                    await c.call_tool("get_parameters", {"sobra": 1}),
                    await c.call_tool("herramienta_inexistente", {})]
    inexistente, argumentos, desconocida = correr(caso())
    for r, kind in ((inexistente, "PARAMETER_NOT_FOUND"), (argumentos, "INVALID_ARGUMENTS"), (desconocida, "UNKNOWN_TOOL")):
        assert r.is_error
        d = json_de(r)
        assert d["ok"] is False and d["error_kind"] == kind and d["mensaje"] and isinstance(d["pistas"], list)


def test_llamadas_simultaneas_se_atienden_una_a_la_vez_sin_romper_el_documento():
    async def caso():
        async with Client(memoria(api.Sesion())) as c:
            await asyncio.gather(*(c.call_tool("create_parameter", {"name": f"p{i}", "expression": f"{i + 1} mm"})
                                   for i in range(6)))
            return json_de(await c.call_tool("get_parameters", {}))
    assert sorted(p["name"] for p in correr(caso())["result"]["parameters"]) == [f"p{i}" for i in range(6)]


# ---------------------------------------------------------------- toolsets
def test_toolsets_filtran_y_lo_no_expuesto_no_se_ejecuta():
    async def caso():
        async with Client(memoria(toolsets=["parametros", "documento"])) as c:
            nombres = [t.name for t in (await c.list_tools()).tools]
            return nombres, await c.call_tool("get_viewport_image", {})
    nombres, bloqueada = correr(caso())
    esperados = [h["nombre"] for h in api.catalogo(["parametros", "documento"])]
    assert nombres == esperados and "get_viewport_image" not in nombres
    assert bloqueada.is_error and json_de(bloqueada)["error_kind"] == "UNKNOWN_TOOL"


def test_por_defecto_no_hay_dev_y_con_dev_estan_todas():
    base = {h["nombre"] for h in api.catalogo() if h["grupo"] != "dev"}
    assert set(memoria().nombres) == base
    assert set(memoria(dev=True).nombres) == {h["nombre"] for h in api.catalogo()}      # con --dev: run_checks y app_screenshot


def test_argumentos_invalidos_de_linea_de_comandos(capsys):
    with pytest.raises(SystemExit) as e:
        main(["--toolsets", "no_existe"])
    assert e.value.code == 2 and "no_existe" in capsys.readouterr().err
    with pytest.raises(SystemExit) as e:
        main(["--port", "27190"])                                   # --port sin --http
    assert e.value.code == 2
    assert main(["--doc", str(RAIZ / "no_existe.omnicad")]) == 2     # abrir falla: corta el arranque
    assert "no se pudo abrir" in capsys.readouterr().err


# ---------------------------------------------------------------- instructions, resources, prompts
def test_instructions_salen_de_flujo_md():
    async def caso():
        async with Client(memoria()) as c:
            return c.instructions
    instrucciones = correr(caso())
    assert (textos.CARPETA_GUIA / "flujo.md").read_text(encoding="utf-8") in instrucciones


def test_resources_y_prompts_se_listan_y_se_leen():
    async def caso():
        async with Client(memoria()) as c:
            return dict(
                recursos=(await c.list_resources()).resources,
                plantillas=(await c.list_resource_templates()).resource_templates,
                prompts=(await c.list_prompts()).prompts,
                fijo=(await c.read_resource("omnicad://guia/flujo")).contents[0].text,
                plantilla=(await c.read_resource("omnicad://guia/indice")).contents[0].text,
                receta=(await c.read_resource("omnicad://receta")).contents[0].text,
                prompt=await c.get_prompt("disenar_pieza", {"descripcion": "un soporte de 40 mm"}))
    r = correr(caso())
    assert {str(x.uri) for x in r["recursos"]} >= {"omnicad://guia/flujo", "omnicad://guia/indice", "omnicad://receta"}
    assert [x.uri_template for x in r["plantillas"]] == ["omnicad://guia/{tema}"]
    assert {p.name for p in r["prompts"]} == {"disenar_pieza", "preparar_impresion_3d", "revisar_diseno"}
    assert r["fijo"] == (textos.CARPETA_GUIA / "flujo.md").read_text(encoding="utf-8")
    assert r["plantilla"] == (textos.CARPETA_GUIA / "indice.md").read_text(encoding="utf-8")
    assert json.loads(r["receta"])["operaciones"]                      # receta del documento de ejemplo
    assert "un soporte de 40 mm" in r["prompt"].messages[0].content.text


def test_tema_de_guia_inexistente_falla():
    async def caso():
        async with Client(memoria()) as c:
            with pytest.raises(MCPError):
                await c.read_resource("omnicad://guia/no_existe")
    correr(caso())


def test_los_prompts_solo_nombran_herramientas_reales():
    nombres = {h["nombre"] for h in api.catalogo()}
    for texto in (textos.disenar_pieza("x"), textos.preparar_impresion_3d(), textos.revisar_diseno()):
        citados = set(re.findall(r"\b[a-z]+(?:_[a-z0-9]+)+\b", texto))
        assert citados and citados <= nombres, citados - nombres


# ---------------------------------------------------------------- extremo a extremo REAL
def test_stdio_real_initialize_list_tools_y_llamadas():
    async def caso():
        t0 = time.perf_counter()
        async with Client(parametros_stdio()) as c:
            arranque = time.perf_counter() - t0
            info = c.server_info
            tools = (await c.list_tools()).tools
            nuevo = await c.call_tool("new_document", {"name": "Prueba MCP"})
            escena = await c.call_tool("get_scene_info", {})
            return arranque, info, tools, nuevo, escena
    arranque, info, tools, nuevo, escena = correr(caso())
    print(f"\nstdio real: {len(tools)} herramientas, arranque + initialize {arranque:.2f} s, "
          f"primeras: {[t.name for t in tools[:5]]}")
    assert (info.name, info.version) == ("omnicad", VERSION)
    assert [t.name for t in tools] == [h["nombre"] for h in api.catalogo(GRUPOS_POR_DEFECTO)]
    assert json_de(nuevo)["result"]["name"] == "Prueba MCP"
    assert json_de(escena)["result"]["name"] == "Prueba MCP" and json_de(escena)["result"]["bodies"] == []


def test_stdio_real_con_doc_abre_el_proyecto_y_devuelve_imagen(tmp_path):
    ruta = tmp_path / "ejemplo.omnicad"
    api.Sesion(crear_documento_ejemplo()).guardar(ruta)

    async def caso():
        async with Client(parametros_stdio("--doc", str(ruta), "--toolsets", "documento,inspeccion")) as c:
            nombres = {t.name for t in (await c.list_tools()).tools}
            escena = await c.call_tool("get_scene_info", {})
            imagen = await c.call_tool("get_viewport_image", {"width": 160, "height": 120})
            return nombres, escena, imagen
    nombres, escena, imagen = correr(caso())
    assert nombres == {h["nombre"] for h in api.catalogo(["documento", "inspeccion"])}
    assert [b["id"] for b in json_de(escena)["result"]["bodies"]] == ["op2.c1", "op6.c1"]
    assert base64.b64decode(imagen.content[1].data)[:8] == FIRMA_PNG


def _puerto_libre():
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def test_http_real_solo_en_127_0_0_1():
    puerto = _puerto_libre()
    proceso = subprocess.Popen([sys.executable, "-m", "omnicad.servidor_mcp", "--modo", "sin_ventana", "--http",
                                "--port", str(puerto)],
                               cwd=RAIZ, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)
    try:
        limite = time.time() + 60
        while time.time() < limite:
            try:
                socket.create_connection(("127.0.0.1", puerto), timeout=1).close()
                break
            except OSError:
                assert proceso.poll() is None, proceso.stderr.read().decode("utf-8", "replace")
                time.sleep(0.3)
        else:
            pytest.fail("el servidor HTTP no abrió el puerto en 60 s")

        async def caso():
            async with Client(f"http://127.0.0.1:{puerto}/mcp") as c:
                tools = (await c.list_tools()).tools
                return len(tools), json_de(await c.call_tool("new_document", {"name": "http"}))
        cantidad, nuevo = correr(caso())
        assert cantidad == len(api.catalogo(GRUPOS_POR_DEFECTO)) and nuevo["result"]["name"] == "http"
        otra_interfaz = socket.gethostbyname(socket.gethostname())    # la IP de la LAN: NO debe aceptar conexiones
        if not otra_interfaz.startswith("127."):
            with pytest.raises(OSError):
                socket.create_connection((otra_interfaz, puerto), timeout=2).close()
    finally:
        proceso.terminate()
        try:
            proceso.wait(10)
        except subprocess.TimeoutExpired:
            proceso.kill()
            proceso.wait(10)
        proceso.stderr.close()
