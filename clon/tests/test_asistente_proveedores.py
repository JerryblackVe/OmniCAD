"""Proveedores Anthropic y OpenAI compatible con urlopen falso: sin red y sin gasto."""
import base64
import io
import json
import urllib.error
import urllib.request

import pytest

from omnicad import api
from omnicad.asistente import bucle
from omnicad.asistente.proveedores import anthropic, openai_compat
from omnicad.asistente.proveedores.base import ErrorProveedor

CLAVE = "sk-prueba-SECRETA-1234567890"
PNG = b"\x89PNG\r\n\x1a\nfalso"
HERRAMIENTAS = [{"nombre": "create_box", "descripcion": "Crea una caja.",
                 "esquema": {"type": "object", "properties": {"length": {"type": "number"}}, "required": [],
                             "additionalProperties": False}}]
CHAT = [
    {"rol": "usuario", "contenido": [{"tipo": "texto", "texto": "Hacé una caja."}]},
    {"rol": "asistente", "contenido": [{"tipo": "texto", "texto": "Voy."},
                                       {"tipo": "pedido_herramienta", "id": "t1", "nombre": "create_box",
                                        "args": {"length": 40}}]},
    {"rol": "usuario", "contenido": [{"tipo": "resultado_herramienta", "id": "t1", "error": False, "contenido": [
        {"tipo": "texto", "texto": '{"ok": true}'}, {"tipo": "imagen", "png": PNG, "ancho": 2, "alto": 3}]}]},
]


class _Respuesta(io.BytesIO):
    def __enter__(self):
        return self

    def __exit__(self, *_):
        return False


@pytest.fixture(autouse=True)
def sin_claves(monkeypatch):
    for variable in ("ANTHROPIC_API_KEY", "OPENAI_API_KEY", "OPENROUTER_API_KEY"):
        monkeypatch.delenv(variable, raising=False)


@pytest.fixture
def red(monkeypatch):
    """Responde en orden los JSON (o excepciones) de `red.respuestas` y guarda cada pedido."""
    class Red:
        respuestas, pedidos = [], []

    def urlopen(pedido, timeout=None):
        Red.pedidos.append({"url": pedido.full_url, "cuerpo": json.loads(pedido.data),
                            "encabezados": {k.lower(): v for k, v in pedido.header_items()}, "timeout": timeout})
        respuesta = Red.respuestas.pop(0)
        if isinstance(respuesta, Exception):
            raise respuesta
        return respuesta if isinstance(respuesta, _Respuesta) else _Respuesta(json.dumps(respuesta).encode())

    Red.respuestas, Red.pedidos = [], []
    monkeypatch.setattr(urllib.request, "urlopen", urlopen)
    return Red


def _http(codigo, cuerpo):
    return urllib.error.HTTPError("https://x", codigo, "error", {}, io.BytesIO(json.dumps(cuerpo).encode()))


def _anthropic(contenido, entrada=1000, salida=500, **extra):
    return {"content": contenido, "usage": {"input_tokens": entrada, "output_tokens": salida},
            "stop_reason": "end_turn", **extra}


def _openai(mensaje, usage=None):
    return {"choices": [{"message": mensaje}], "usage": usage or {"prompt_tokens": 10, "completion_tokens": 4}}


def test_anthropic_arma_el_pedido(red):
    red.respuestas = [_anthropic([{"type": "text", "text": "Hecho"}])]
    anthropic.ProveedorAnthropic(clave=CLAVE, timeout=7).responder("Sos el asistente.", CHAT, HERRAMIENTAS)
    pedido = red.pedidos[0]
    assert pedido["url"] == "https://api.anthropic.com/v1/messages" and pedido["timeout"] == 7
    assert pedido["encabezados"]["x-api-key"] == CLAVE
    assert pedido["encabezados"]["anthropic-version"] == "2023-06-01"
    cuerpo = pedido["cuerpo"]
    # caché del prompt (IA-11): marca en el sistema, en la última herramienta y arriba del todo (la conversación)
    cache = {"type": "ephemeral"}
    assert cuerpo["model"] == "claude-opus-5-5" and cuerpo["cache_control"] == cache
    assert cuerpo["system"] == [{"type": "text", "text": "Sos el asistente.", "cache_control": cache}]
    assert cuerpo["tools"] == [{"name": "create_box", "description": "Crea una caja.",
                                "input_schema": HERRAMIENTAS[0]["esquema"], "cache_control": cache}]
    assert cuerpo["messages"][1] == {"role": "assistant", "content": [
        {"type": "text", "text": "Voy."}, {"type": "tool_use", "id": "t1", "name": "create_box", "input": {"length": 40}}]}
    assert cuerpo["messages"][2] == {"role": "user", "content": [{
        "type": "tool_result", "tool_use_id": "t1", "is_error": False, "content": [
            {"type": "text", "text": '{"ok": true}'},
            {"type": "image", "source": {"type": "base64", "media_type": "image/png",
                                         "data": base64.b64encode(PNG).decode()}}]}]}


def test_anthropic_sin_sistema_ni_herramientas_no_manda_esos_campos(red):
    red.respuestas = [_anthropic([{"type": "text", "text": "Hola"}])]
    anthropic.ProveedorAnthropic(clave=CLAVE).responder("", CHAT[:1], [])
    assert "system" not in red.pedidos[0]["cuerpo"] and "tools" not in red.pedidos[0]["cuerpo"]


def test_anthropic_traduce_la_respuesta_y_el_costo(red):
    red.respuestas = [_anthropic([{"type": "thinking", "thinking": ""}, {"type": "text", "text": "Creo la caja."},
                                  {"type": "tool_use", "id": "toolu_1", "name": "create_box", "input": {"length": 40}}])]
    respuesta = anthropic.ProveedorAnthropic(clave=CLAVE).responder("", CHAT[:1], HERRAMIENTAS)
    assert respuesta.texto == "Creo la caja."
    assert [(p.id, p.nombre, p.args) for p in respuesta.herramientas] == [("toolu_1", "create_box", {"length": 40})]
    assert respuesta.uso == {"entrada": 1000, "salida": 500, "costo_usd": pytest.approx(0.014)}
    assert anthropic.costo_usd("modelo-desconocido", 1000, 500) is None
    # con caché: la leída cuesta 0,1× y la escrita 1,25× la entrada; «entrada» suma las tres
    red.respuestas = [{"content": [{"type": "text", "text": "ok"}], "usage": {
        "input_tokens": 100, "output_tokens": 500, "cache_creation_input_tokens": 1000,
        "cache_read_input_tokens": 10000}}]
    respuesta = anthropic.ProveedorAnthropic(clave=CLAVE).responder("", CHAT[:1], HERRAMIENTAS)
    assert respuesta.uso == {"entrada": 11100, "salida": 500,
                             "costo_usd": pytest.approx((100 + 1250 + 1000) * 4 / 1e6 + 500 * 20 / 1e6)}


def test_anthropic_negativa_es_error_claro(red):
    red.respuestas = [_anthropic([], stop_reason="refusal", stop_details={"category": "cyber"})]
    with pytest.raises(ErrorProveedor, match="cyber"):
        anthropic.ProveedorAnthropic(clave=CLAVE).responder("", CHAT[:1], [])


def test_anthropic_clave_por_entorno_o_error(red, monkeypatch):
    with pytest.raises(ErrorProveedor, match="ANTHROPIC_API_KEY"):
        anthropic.ProveedorAnthropic()
    monkeypatch.setenv("ANTHROPIC_API_KEY", CLAVE)
    assert anthropic.ProveedorAnthropic().clave == CLAVE


def test_openai_arma_el_pedido_con_imagenes_tras_los_resultados(red):
    red.respuestas = [_openai({"content": "Hecho"})]
    openai_compat.ProveedorOpenAI("gpt-x", clave=CLAVE).responder("Sos el asistente.", CHAT, HERRAMIENTAS)
    pedido = red.pedidos[0]
    assert pedido["url"] == "https://api.openai.com/v1/chat/completions"
    assert pedido["encabezados"]["authorization"] == f"Bearer {CLAVE}"
    cuerpo = pedido["cuerpo"]
    assert cuerpo["tools"] == [{"type": "function", "function": {"name": "create_box", "description": "Crea una caja.",
                                                                 "parameters": HERRAMIENTAS[0]["esquema"]}}]
    assert cuerpo["messages"] == [
        {"role": "system", "content": "Sos el asistente."},
        {"role": "user", "content": [{"type": "text", "text": "Hacé una caja."}]},
        {"role": "assistant", "content": "Voy.", "tool_calls": [
            {"id": "t1", "type": "function", "function": {"name": "create_box", "arguments": '{"length": 40}'}}]},
        {"role": "tool", "tool_call_id": "t1", "content": '{"ok": true}'},
        {"role": "user", "content": [{"type": "image_url", "image_url": {
            "url": "data:image/png;base64," + base64.b64encode(PNG).decode()}}]},
    ]


def test_openai_ollama_sin_clave_no_manda_authorization(red, monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", CLAVE)
    red.respuestas = [_openai({"content": "Hola"}), _openai({"content": "Hola"})]
    openai_compat.ProveedorOpenAI("qwen3", base_url=openai_compat.OLLAMA, clave="").responder("", CHAT[:1], [])
    monkeypatch.delenv("OPENAI_API_KEY")
    openai_compat.ProveedorOpenAI("qwen3", base_url=openai_compat.OLLAMA).responder("", CHAT[:1], [])
    assert red.pedidos[0]["encabezados"]["authorization"] == f"Bearer {CLAVE}"  # clave vacía = la del entorno
    assert "authorization" not in red.pedidos[1]["encabezados"]
    assert red.pedidos[1]["url"] == "http://localhost:11434/v1/chat/completions"
    assert "tools" not in red.pedidos[1]["cuerpo"]


def test_openai_traduce_respuesta_uso_y_costo_de_openrouter(red, monkeypatch):
    monkeypatch.setenv("OPENROUTER_API_KEY", CLAVE)
    red.respuestas = [_openai({"content": None, "tool_calls": [
        {"id": "c1", "type": "function", "function": {"name": "create_box", "arguments": '{"length": 40}'}},
        {"type": "function", "function": {"name": "create_box", "arguments": "{roto"}}]},
        {"prompt_tokens": 120, "completion_tokens": 30, "cost": 0.0021})]
    proveedor = openai_compat.ProveedorOpenAI("anthropic/claude-sonnet-5-5", base_url=openai_compat.OPENROUTER)
    respuesta = proveedor.responder("", CHAT[:1], HERRAMIENTAS)
    assert red.pedidos[0]["encabezados"]["authorization"] == f"Bearer {CLAVE}"
    assert respuesta.texto == ""
    assert [(p.id, p.nombre, p.args) for p in respuesta.herramientas] == [
        ("c1", "create_box", {"length": 40}), ("llamada_1", "create_box", {"_argumentos_invalidos": "{roto"})]
    assert respuesta.uso == {"entrada": 120, "salida": 30, "costo_usd": 0.0021}


def test_openai_respuesta_sin_mensaje(red):
    red.respuestas = [{"choices": []}]
    with pytest.raises(ErrorProveedor, match="ningún mensaje"):
        openai_compat.ProveedorOpenAI("m", base_url=openai_compat.OLLAMA).responder("", CHAT[:1], [])


def _proveedores():
    return [anthropic.ProveedorAnthropic(clave=CLAVE), openai_compat.ProveedorOpenAI("gpt-x", clave=CLAVE)]


@pytest.mark.parametrize("codigo, texto", [(401, "clave de API no es válida"), (403, "no tiene permiso"),
                                           (429, "límite de pedidos"), (503, "Probá de nuevo"), (400, "rechazó")])
@pytest.mark.parametrize("indice", [0, 1])
def test_errores_http_claros_y_sin_la_clave(red, codigo, texto, indice):
    red.respuestas = [_http(codigo, {"error": {"message": "x" * 260 + f" Incorrect API key provided: {CLAVE}"}})]
    with pytest.raises(ErrorProveedor) as info:
        _proveedores()[indice].responder("", CHAT[:1], [])
    mensaje = str(info.value)
    assert texto in mensaje and f"HTTP {codigo}" in mensaje
    assert CLAVE[:8] not in mensaje and "***" in mensaje
    assert info.value.__cause__ is None and info.value.__suppress_context__


@pytest.mark.parametrize("falla, texto", [(urllib.error.URLError("sin red"), "No se pudo conectar"),
                                          (TimeoutError(), "no respondió en 300 s"),
                                          (ConnectionResetError("cortada"), "No se pudo conectar"),
                                          (_Respuesta(b"no es json"), "no es JSON")])
def test_errores_de_conexion(red, falla, texto):
    red.respuestas = [falla]
    with pytest.raises(ErrorProveedor, match=texto):
        _proveedores()[0].responder("", CHAT[:1], [])


@pytest.mark.parametrize("proveedor, respuestas", [
    (lambda: anthropic.ProveedorAnthropic(clave=CLAVE),
     [_anthropic([{"type": "tool_use", "id": "toolu_1", "name": "create_box",
                   "input": {"length": 40, "width": 40, "height": 40}}]),
      _anthropic([{"type": "text", "text": "Listo"}])]),
    (lambda: openai_compat.ProveedorOpenAI("qwen3", base_url=openai_compat.OLLAMA),
     [_openai({"content": None, "tool_calls": [{"id": "c1", "type": "function", "function": {
         "name": "create_box", "arguments": '{"length": 40, "width": 40, "height": 40}'}}]}),
      _openai({"content": "Listo"})]),
])
def test_punta_a_punta_crea_una_caja(red, proveedor, respuestas):
    sesion = api.Sesion()
    red.respuestas = respuestas
    mensajes = [{"rol": "usuario", "contenido": [{"tipo": "texto", "texto": "Creá una caja de 40 mm."}]}]
    resultado = bucle.correr(proveedor(), mensajes, lambda n, a: api.llamar(sesion, n, a))
    assert resultado["motivo"] == "fin" and resultado["vueltas"] == 2
    assert len(sesion.doc.estado_final.cuerpos) == 1
    assert mensajes[-1] == {"rol": "asistente", "contenido": [{"tipo": "texto", "texto": "Listo"}]}
    segundo = json.dumps(red.pedidos[1]["cuerpo"])
    assert '"ok\\": true' in segundo and "buscar_herramientas" in segundo
