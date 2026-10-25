# -*- coding: utf-8 -*-
"""Herramientas del grupo `asistente` (api/herramientas_asistente.py): configuración, pedido sin ventana con un
proveedor falso (sin red ni gasto), historial y su lugar en el MCP y la CLI."""
import json

import pytest

from omnicad import api
from omnicad.asistente import config, historial
from omnicad.asistente.proveedores.base import ErrorProveedor, PedidoHerramienta, ProveedorFalso, Respuesta
from omnicad.servidor_mcp.servidor import GRUPOS_CONOCIDOS, GRUPOS_POR_DEFECTO

CLAVE_FALSA = "sk-FALSA-api-asistente-0123456789"
CAJA = PedidoHerramienta("h1", "create_box", {"length": 40, "width": 30, "height": 20})
CILINDRO = PedidoHerramienta("h2", "create_cylinder", {"radius": 5, "height": 10})


@pytest.fixture(autouse=True)
def aislado(tmp_path, monkeypatch):
    monkeypatch.setenv("OMNICAD_AJUSTES_INI", str(tmp_path / "prefs.ini"))
    monkeypatch.setenv(historial.VAR_CARPETA, str(tmp_path / "chats"))
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)


def falso(monkeypatch, *respuestas):
    monkeypatch.setattr(config, "crear_proveedor", lambda cfg: ProveedorFalso(list(respuestas)))


def test_config_por_defecto_y_la_clave_nunca_sale(monkeypatch):
    s = api.Sesion()
    r = api.llamar(s, "get_assistant_config")["result"]
    assert r | {"providers": None} == {"provider": "anthropic", "model": "", "effective_model": "claude-opus-5-5",
                                       "base_url": "", "default_mode": "guiar", "max_usd": 0.5, "send_images": True,
                                       "key_env_var": "ANTHROPIC_API_KEY", "key_set": False, "providers": None}
    monkeypatch.setenv("ANTHROPIC_API_KEY", CLAVE_FALSA)
    r = api.llamar(s, "get_assistant_config")
    assert r["result"]["key_set"] is True and CLAVE_FALSA not in json.dumps(r)


def test_set_cambia_solo_lo_pasado_y_valida(tmp_path, monkeypatch):
    s = api.Sesion()
    monkeypatch.setenv("OPENAI_API_KEY", CLAVE_FALSA)
    r = api.llamar(s, "set_assistant_config", {"provider": "local", "model": "qwen3:8b",
                                                "base_url": "http://localhost:11434/v1", "max_usd": 0, "send_images": False})
    assert r["ok"] and r["result"]["updated"] == ["base_url", "imagenes", "modelo", "proveedor", "tope_usd"]
    leido = api.llamar(s, "get_assistant_config")["result"]
    assert (leido["provider"], leido["model"], leido["max_usd"], leido["send_images"], leido["default_mode"]) == \
        ("local", "qwen3:8b", 0.0, False, "guiar")
    assert CLAVE_FALSA not in (tmp_path / "prefs.ini").read_text(encoding="utf-8")
    for args, texto in [({"provider": "otro"}, "Proveedor desconocido"),
                        ({"base_url": "https://malo.example.com/v1"}, "base_url"),
                        ({"base_url": "ftp://localhost/"}, "base_url"),
                        ({"max_usd": 101}, "max_usd"), ({"max_usd": -1}, "max_usd"),
                        ({"model": "a\nb"}, "modelo"), ({"default_mode": "todo"}, ""),
                        ({"api_key": CLAVE_FALSA}, ""), ({"ruta_claude_code": "C:/x.exe"}, "")]:
        r = api.llamar(s, "set_assistant_config", args)
        assert r["error_kind"] == "INVALID_ARGUMENTS" and texto in r["mensaje"], args
    assert api.llamar(s, "set_assistant_config", {"base_url": "https://openrouter.ai/api/v1"})["ok"]
    assert api.llamar(s, "get_assistant_config")["result"]["provider"] == "local"   # lo rechazado no cambió nada


def test_ask_crea_una_caja_y_un_undo_la_saca_entera(monkeypatch):
    s = api.Sesion()
    falso(monkeypatch, Respuesta(herramientas=[CAJA], uso={"entrada": 10, "salida": 5, "costo_usd": 0.001}),
          Respuesta(herramientas=[CILINDRO]), Respuesta(texto="Listo: caja y cilindro."))
    r = api.llamar(s, "assistant_ask", {"prompt": "hace una caja y un cilindro"})
    assert r["ok"], r
    assert r["result"] | {"usage": None} == {"text": "Listo: caja y cilindro.", "stop_reason": "fin", "turns": 3,
                                             "tools": [{"name": "create_box", "ok": True},
                                                       {"name": "create_cylinder", "ok": True}], "usage": None}
    assert r["result"]["usage"] == {"input_tokens": 10, "output_tokens": 5, "cost_usd": 0.001}
    assert any("aprobaron solos" in a for a in r["avisos"])
    assert len(s.doc.operaciones) == 2
    assert api.llamar(s, "undo")["ok"] and s.doc.operaciones == []      # UN paso de deshacer para todo el pedido


def test_ask_explicar_no_cambia_nada(monkeypatch):
    s = api.Sesion()
    falso(monkeypatch, Respuesta(herramientas=[CAJA]), Respuesta(texto="Se hace con Caja."))
    r = api.llamar(s, "assistant_ask", {"prompt": "como hago una caja", "mode": "explicar"})
    assert r["ok"] and r["result"]["tools"] == [{"name": "create_box", "ok": False}] and s.doc.operaciones == []
    assert not any("aprobaron solos" in a for a in r["avisos"])


def test_ask_tope_de_gasto_vuelve_atras(monkeypatch):
    s = api.Sesion()
    falso(monkeypatch, Respuesta(herramientas=[CAJA], uso={"costo_usd": 0.9}), Respuesta(herramientas=[CILINDRO]))
    r = api.llamar(s, "assistant_ask", {"prompt": "caja"})
    assert r["error_kind"] == "BUDGET_EXCEEDED" and s.doc.operaciones == []


def test_ask_errores_claros(monkeypatch):
    s = api.Sesion()
    assert api.llamar(s, "assistant_ask", {"prompt": "   "})["error_kind"] == "INVALID_ARGUMENTS"
    r = api.llamar(s, "assistant_ask", {"prompt": "hola"})            # sin clave de verdad: crear_proveedor falla
    assert r["error_kind"] == "PROVIDER_ERROR" and "ANTHROPIC_API_KEY" in r["mensaje"]

    def roto(cfg):
        raise ErrorProveedor("no hay red")
    monkeypatch.setattr(config, "crear_proveedor", roto)
    assert api.llamar(s, "assistant_ask", {"prompt": "hola"})["mensaje"] == "no hay red"
    api.llamar(s, "set_assistant_config", {"provider": "claude_code"})
    r = api.llamar(s, "assistant_ask", {"prompt": "hola"})
    assert r["error_kind"] == "PROVIDER_ERROR" and "ventana" in r["mensaje"]


def test_chats_desde_el_catalogo():
    s = api.Sesion()
    id_chat = historial.guardar([{"rol": "usuario", "contenido": [{"tipo": "texto", "texto": "hola"}]},
                                 {"rol": "asistente", "contenido": [{"tipo": "texto", "texto": "chau"},
                                                                    {"tipo": "pedido_herramienta", "id": "1",
                                                                     "nombre": "undo", "args": {}}]}],
                                "explicar", "local", "qwen3")
    lista = api.llamar(s, "list_assistant_chats")["result"]["chats"]
    assert [(c["id"], c["title"], c["messages"]) for c in lista] == [(id_chat, "hola", 2)]
    chat = api.llamar(s, "get_assistant_chat", {"chat_id": id_chat})["result"]
    assert chat["messages"] == [{"role": "usuario", "text": "hola"}, {"role": "asistente", "text": "chau"},
                                {"role": "asistente", "tool": "undo", "args": {}}]
    assert api.llamar(s, "get_assistant_chat", {"chat_id": "../x"})["error_kind"] == "NOT_FOUND"


def test_grupo_fuera_de_los_por_defecto_del_mcp_y_fuera_del_propio_asistente():
    from omnicad.asistente.herramientas import Herramientas
    assert "asistente" in GRUPOS_CONOCIDOS and "asistente" not in GRUPOS_POR_DEFECTO
    assert not {h["nombre"] for h in api.catalogo(["asistente"])} & set(Herramientas().catalogo)


def test_cli_assistant_ask(monkeypatch, capsys, tmp_path):
    from omnicad.cli import main
    assert main(["assistant_ask", "--help"]) == 0 and "GASTA" in capsys.readouterr().out
    falso(monkeypatch, Respuesta(herramientas=[CAJA]), Respuesta(texto="Hecho."))
    doc = tmp_path / "pieza.omnicad"
    assert main(["new", str(doc)]) == 0
    capsys.readouterr()
    assert main(["assistant_ask", "hace una caja", "--doc", str(doc), "--json"]) == 0
    salida = json.loads(capsys.readouterr().out)
    assert salida["ok"] and salida["result"]["text"] == "Hecho."
    assert main(["info", str(doc), "--json"]) == 0
    assert len(json.loads(capsys.readouterr().out)["result"]["bodies"]) == 1     # se guardó con la caja
