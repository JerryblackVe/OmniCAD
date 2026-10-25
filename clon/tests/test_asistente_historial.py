# -*- coding: utf-8 -*-
"""Historial de chats del Asistente (asistente/historial.py): sin Qt, sin red."""
import json

import pytest

from omnicad.asistente import historial

CLAVE_FALSA = "sk-ant-FALSA-0123456789abcdef"


@pytest.fixture(autouse=True)
def carpeta(tmp_path, monkeypatch):
    monkeypatch.setenv(historial.VAR_CARPETA, str(tmp_path))
    return tmp_path


def chat(texto="hace una caja de cuarenta milimetros con empalme de tres y agujero", png=b"\x89PNG..."):
    return [{"rol": "usuario", "contenido": [{"tipo": "texto", "texto": texto}]},
            {"rol": "asistente", "contenido": [{"tipo": "pedido_herramienta", "id": "h1", "nombre": "create_box",
                                                "args": {"length": 40}}]},
            {"rol": "usuario", "contenido": [{"tipo": "resultado_herramienta", "id": "h1", "error": False,
                                              "contenido": [{"tipo": "texto", "texto": "{\"ok\": true}"},
                                                            {"tipo": "imagen", "png": png, "ancho": 4, "alto": 3}]}]},
            {"rol": "asistente", "contenido": [{"tipo": "texto", "texto": "Listo."}]}]


def test_guardar_listar_cargar_y_borrar(carpeta):
    id_a = historial.guardar(chat(), "hacer", "anthropic", "claude-opus-5-5")
    id_b = historial.guardar(chat("otra cosa"), "explicar", "local", "qwen3", sesiones_cli={"opencode": "s1"})
    assert sorted(p.name for p in carpeta.iterdir()) == sorted([f"{id_a}.json", f"{id_b}.json"])
    lista = historial.listar()
    assert [c["id"] for c in lista] == [id_b, id_a]            # el más nuevo primero
    assert lista[1] | {"fecha": ""} == {"id": id_a, "titulo": "hace una caja de cuarenta milimetros con empalme…",
                                       "fecha": "", "modo": "hacer", "proveedor": "anthropic",
                                       "modelo": "claude-opus-5-5", "mensajes": 4}
    cargado = historial.cargar(id_a)
    assert cargado["mensajes"] == chat()                       # las imágenes vuelven en bytes
    assert historial.cargar(id_b)["sesiones_cli"] == {"opencode": "s1"}
    # Seguir el chat: se reescribe el mismo archivo.
    assert historial.guardar(chat() + chat("y otra"), "hacer", "anthropic", "", id_a) == id_a
    assert historial.listar()[0]["id"] == id_a and historial.listar()[0]["mensajes"] == 8
    historial.borrar(id_a)
    assert [c["id"] for c in historial.listar()] == [id_b]
    with pytest.raises(historial.ErrorHistorial, match="No existe"):
        historial.borrar(id_a)
    with pytest.raises(historial.ErrorHistorial, match="No existe"):
        historial.cargar(id_a)


def test_nunca_guarda_la_clave(carpeta, monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", CLAVE_FALSA)
    monkeypatch.setenv("OPENAI_API_KEY", CLAVE_FALSA)
    historial.guardar(chat(), "hacer", "anthropic", "claude-opus-5-5", sesiones_cli={"claude_code": "s"})
    for archivo in carpeta.iterdir():
        assert CLAVE_FALSA not in archivo.read_text(encoding="utf-8")


def test_imagen_grande_se_descarta_con_marca(carpeta, monkeypatch):
    monkeypatch.setattr(historial, "TOPE_IMAGEN", 10)
    id_chat = historial.guardar(chat(png=b"x" * 2048), "hacer", "anthropic", "")
    resultado = historial.cargar(id_chat)["mensajes"][2]["contenido"][0]["contenido"]
    assert resultado[1] == {"tipo": "texto", "texto": "(imagen no guardada en el historial: pesaba 2 KB)"}


def test_archivo_roto_no_tira_nada(carpeta):
    id_bueno = historial.guardar(chat(), "hacer", "anthropic", "")
    (carpeta / "20260101-000000-aaaaaa.json").write_text("{esto no es json", encoding="utf-8")
    (carpeta / "20260101-000000-bbbbbb.json").write_text(json.dumps({"mensajes": [{"rol": "usuario",
                                                         "contenido": [{"tipo": "imagen", "png": "%%%"}]}]}),
                                                         encoding="utf-8")
    assert {c["id"] for c in historial.listar()} == {id_bueno, "20260101-000000-bbbbbb"}   # el ilegible no se lista
    (carpeta / "20260101-000000-cccccc.json").write_text(json.dumps({"mensajes": [{"rol": "usuario",
                                                         "contenido": [{"tipo": "texto"}]}]}), encoding="utf-8")
    for roto in ("20260101-000000-aaaaaa", "20260101-000000-bbbbbb", "20260101-000000-cccccc"):
        with pytest.raises(historial.ErrorHistorial, match="dañado"):
            historial.cargar(roto)


@pytest.mark.parametrize("malo", ["../afuera", "..\\x", "C:/Windows/x", "", None, 5])
def test_id_que_no_es_un_nombre_de_chat_se_rechaza(malo):
    with pytest.raises(historial.ErrorHistorial, match="inválido"):
        historial.cargar(malo)
    with pytest.raises(historial.ErrorHistorial, match="inválido"):
        historial.borrar(malo)


def test_titulo_sin_texto():
    assert historial.titulo_de([]) == "Chat sin título"
    assert historial.titulo_de(chat("  corto  ")) == "corto"
