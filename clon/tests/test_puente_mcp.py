# -*- coding: utf-8 -*-
"""Lado MCP del puente en vivo, sin Qt: un servidor de puente FALSO (hilo con socket) prueba el cliente, el modo
vivo, el modo auto y el aviso cuando cambia de un modo al otro."""
import asyncio
import json
import socket
import threading

import pytest
from mcp.client import Client

from omnicad import api
from omnicad.api import protocolo_puente as proto
from omnicad.servidor_mcp import crear_servidor, main
from omnicad.servidor_mcp.puente_cliente import ClientePuente
from omnicad.servidor_mcp.servidor import AVISO_SIN_VENTANA, AVISO_VIVO

PNG = b"\x89PNG\r\n\x1a\n" + b"x" * 20


class PuenteFalso:
    """Imita a la app: escucha en 127.0.0.1, escribe puente.json y contesta líneas JSON."""

    def __init__(self, archivo, mudo=False):
        self.archivo, self.mudo, self.token = archivo, mudo, "token-de-prueba"
        self.pedidos, self.conexiones = [], []
        self.s = socket.socket()
        self.s.bind(("127.0.0.1", 0))
        self.s.listen()
        self.s.settimeout(0.2)
        self.puerto = self.s.getsockname()[1]
        self.activo = True
        self.hilo = threading.Thread(target=self._bucle, daemon=True)
        self.hilo.start()
        proto.escribir_info(archivo, {"port": self.puerto, "token": self.token, "pid": 1, "version": "x", "protocol": 1})

    def _bucle(self):
        while self.activo:
            try:
                conexion, _ = self.s.accept()
            except OSError:
                continue
            self.conexiones.append(conexion)
            threading.Thread(target=self._atender, args=(conexion,), daemon=True).start()

    def _atender(self, conexion):
        buffer = b""
        with conexion:
            while self.activo:
                try:
                    trozo = conexion.recv(65536)
                except OSError:
                    return
                if not trozo:
                    return
                buffer += trozo
                while b"\n" in buffer:
                    linea, _, buffer = buffer.partition(b"\n")
                    pedido = json.loads(linea)
                    self.pedidos.append(pedido)
                    if self.mudo:
                        continue
                    conexion.sendall(proto.linea({"id": pedido["id"], **self._respuesta(pedido)}))
                    if pedido["token"] != self.token:
                        return

    def _respuesta(self, pedido):
        if pedido["token"] != self.token:
            return api.errores.error("UNAUTHORIZED", "Token incorrecto.").a_dict()
        if pedido["tool"] == "status":
            return {"ok": True, "result": {"document": "Doc de la ventana", "busy": False}, "avisos": []}
        if pedido["tool"] == "get_viewport_image":
            return {"ok": True, "result": proto.a_cable({"image": api.Imagen(PNG, 4, 3)}), "avisos": []}
        return {"ok": True, "result": {"vivo": True, "tool": pedido["tool"], "args": pedido["args"]}, "avisos": []}

    def apagar(self):
        self.activo = False
        self.s.close()
        for conexion in self.conexiones:              # como la app al apagar el puente: corta las conexiones
            try:
                conexion.shutdown(socket.SHUT_RDWR)
            except OSError:
                pass
            conexion.close()
        proto.borrar_info(self.archivo, self.token)
        self.hilo.join(2)


@pytest.fixture
def archivo(tmp_path):
    return tmp_path / "puente.json"


def correr(coro):
    return asyncio.run(asyncio.wait_for(coro, 60))


# ---------------------------------------------------------------- cliente
def test_cliente_llama_y_reconstruye_las_imagenes(archivo):
    falso = PuenteFalso(archivo)
    try:
        c = ClientePuente(archivo)
        r = c.llamar("create_box", {"length": 1})
        assert r == {"ok": True, "result": {"vivo": True, "tool": "create_box", "args": {"length": 1}}, "avisos": []}
        imagen = c.llamar("get_viewport_image", {})["result"]["image"]
        assert isinstance(imagen, api.Imagen) and (imagen.png, imagen.ancho, imagen.alto) == (PNG, 4, 3)
        assert [p["token"] for p in falso.pedidos] == [falso.token] * 2
        assert [p["id"] for p in falso.pedidos] == [1, 2]
        c.cerrar()
    finally:
        falso.apagar()


def test_cliente_sin_app_da_app_not_running_y_token_malo_unauthorized(archivo):
    r = ClientePuente(archivo).llamar("get_scene_info")
    assert r["ok"] is False and r["error_kind"] == "APP_NOT_RUNNING" and any("--puente" in p for p in r["pistas"])
    falso = PuenteFalso(archivo)
    try:
        info = proto.leer_info(archivo)
        proto.escribir_info(archivo, {**info, "token": "otro"})          # puente.json de otra instancia
        c = ClientePuente(archivo)
        assert c.llamar("get_scene_info")["error_kind"] == "UNAUTHORIZED" and c.info is None
    finally:
        falso.apagar()


def test_cliente_con_app_que_no_contesta_da_app_not_responding(archivo):
    falso = PuenteFalso(archivo, mudo=True)
    try:
        r = ClientePuente(archivo, tiempo_respuesta=0.3).llamar("get_scene_info")
        assert r["error_kind"] == "APP_NOT_RESPONDING" and r["pistas"]
    finally:
        falso.apagar()


def test_cliente_reconecta_si_la_app_se_reinicio(archivo):
    falso = PuenteFalso(archivo)
    c = ClientePuente(archivo)
    assert c.llamar("ping")["ok"]
    falso.apagar()
    falso = PuenteFalso(archivo)                                         # otro puerto y otro proceso
    try:
        assert c.llamar("ping")["ok"] and c.info["port"] == falso.puerto
    finally:
        falso.apagar()


# ---------------------------------------------------------------- modos del servidor MCP
def _json(r):
    return json.loads(r.content[0].text)


def test_modo_vivo_sin_app_y_con_app(archivo):
    servidor = crear_servidor(api.Sesion(), modo="vivo", cliente=ClientePuente(archivo))

    async def caso(falso=None):
        async with Client(servidor) as c:
            nombres = [t.name for t in (await c.list_tools()).tools]
            return nombres, await c.call_tool("create_box", {"length": 1, "width": 1, "height": 1})
    nombres, r = correr(caso())
    assert "get_mode" in nombres and r.is_error and _json(r)["error_kind"] == "APP_NOT_RUNNING"
    falso = PuenteFalso(archivo)
    try:
        _, r = correr(caso())
        assert not r.is_error and _json(r)["result"]["vivo"] is True and _json(r)["avisos"] == []
    finally:
        falso.apagar()


def test_modo_auto_cambia_de_documento_y_lo_avisa(archivo):
    sesion = api.Sesion()
    sesion.doc.nombre = "Doc del servidor"
    servidor = crear_servidor(sesion, modo="auto", cliente=ClientePuente(archivo))

    async def llamar(nombre, args=None):
        async with Client(servidor) as c:
            return _json(await c.call_tool(nombre, args or {}))

    sin_app = correr(llamar("get_scene_info"))
    assert sin_app["result"]["name"] == "Doc del servidor" and sin_app["avisos"] == []     # arranca sin ventana: sin aviso
    assert correr(llamar("get_mode"))["result"]["active"] == "sin_ventana"
    falso = PuenteFalso(archivo)
    try:
        vivo = correr(llamar("create_box", {"length": 1, "width": 1, "height": 1}))
        assert vivo["result"]["vivo"] is True
        assert vivo["avisos"] == [AVISO_VIVO.format(doc="«Doc de la ventana»")]
        otra = correr(llamar("get_scene_info"))
        assert otra["result"]["vivo"] is True and otra["avisos"] == []                    # sin cambio: sin aviso
        modo = correr(llamar("get_mode"))["result"]
        assert modo["active"] == "vivo" and modo["app"]["document"] == "Doc de la ventana"
    finally:
        falso.apagar()
    de_vuelta = correr(llamar("get_scene_info"))
    assert de_vuelta["result"]["name"] == "Doc del servidor" and de_vuelta["avisos"] == [
        AVISO_SIN_VENTANA.format(doc="«Doc del servidor»")]
    assert len(sesion.doc.operaciones) == 0                    # el create_box fue a la app, no a la sesión propia


def test_sin_ventana_no_suma_get_mode_y_doc_con_vivo_es_error_de_uso(capsys):
    assert "get_mode" not in crear_servidor(api.Sesion()).nombres
    with pytest.raises(SystemExit) as e:
        main(["--modo", "vivo", "--doc", "x.omnicad"])
    assert e.value.code == 2 and "--modo vivo" in capsys.readouterr().err
