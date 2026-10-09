# -*- coding: utf-8 -*-
"""Puente en vivo (ui/puente.py) con la ventana real en modo offscreen y un cliente QTcpSocket que NO bloquea el
hilo de Qt (el servidor corre en ese mismo hilo: un socket bloqueante lo trabaría)."""
import base64
import json
import os
import time

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtCore import QSettings  # noqa: E402
from PySide6.QtNetwork import QAbstractSocket, QHostAddress, QTcpSocket  # noqa: E402
from PySide6.QtTest import QTest  # noqa: E402

from omnicad.api import protocolo_puente as proto  # noqa: E402

FIRMA_PNG = b"\x89PNG\r\n\x1a\n"


@pytest.fixture(scope="module")
def app_qt():
    from PySide6.QtWidgets import QApplication
    return QApplication.instance() or QApplication([])


@pytest.fixture(scope="module")
def ventana(app_qt, tmp_path_factory):
    from omnicad.ui.preferencias import Preferencias
    from omnicad.ui.ventana import VentanaPrincipal
    carpeta = tmp_path_factory.mktemp("puente")
    anterior = os.environ.get(proto.VARIABLE_CARPETA)
    os.environ[proto.VARIABLE_CARPETA] = str(carpeta)          # nunca el puente.json real del usuario
    v = VentanaPrincipal(prefs=Preferencias(QSettings(str(carpeta / "preferencias.ini"), QSettings.IniFormat)))
    v.show()
    yield v
    v.doc.modificado = False
    v.close()
    v.deleteLater()
    QTest.qWait(1)
    if anterior is None:
        os.environ.pop(proto.VARIABLE_CARPETA, None)
    else:
        os.environ[proto.VARIABLE_CARPETA] = anterior


@pytest.fixture
def puente(ventana):
    """Puente encendido sobre un documento vacío y sin cambios; se apaga al terminar."""
    from omnicad.timeline.documento import Documento
    ventana.set_documento(Documento())
    assert ventana.encender_puente()
    yield ventana.puente
    ventana._puente_sesion = False
    ventana._aplicar_puente()


class Cliente:
    """Cliente de líneas JSON con QTcpSocket: espera procesando eventos (QTest.qWait), nunca bloqueando."""

    def __init__(self, puerto, token):
        self.token, self.n, self.buffer = token, 0, b""
        self.s = QTcpSocket()
        self.s.connectToHost(QHostAddress(QHostAddress.SpecialAddress.LocalHost), puerto)
        self._esperar(lambda: self.s.state() == QAbstractSocket.SocketState.ConnectedState, "conectar")

    def _esperar(self, condicion, que, segundos=20):
        limite = time.time() + segundos
        while not condicion():
            assert time.time() < limite, f"tiempo agotado esperando {que}"
            QTest.qWait(5)

    def pedir(self, tool, args=None, token=None):
        self.n += 1
        pedido = {"id": self.n, "token": self.token if token is None else token, "tool": tool, "args": args or {}}
        self.s.write(proto.linea(pedido))
        self.s.flush()
        respuesta = self.leer(f"la respuesta de {tool}")
        assert respuesta.pop("id") == self.n
        return respuesta

    def leer(self, que="la respuesta"):
        def hay_linea():
            self.buffer += bytes(self.s.readAll())
            return b"\n" in self.buffer
        self._esperar(hay_linea, que)
        texto, _, self.buffer = self.buffer.partition(b"\n")
        return json.loads(texto)

    def cerrar(self):
        self.s.disconnectFromHost()
        self.s.deleteLater()


def _cliente(puente):
    info = proto.leer_info()
    return Cliente(info["port"], info["token"])


# ---------------------------------------------------------------- archivo de descubrimiento
def test_puente_json_se_crea_al_encender_y_se_borra_al_apagar(puente, ventana):
    info = proto.leer_info()
    assert proto.ruta_info().parent == proto.carpeta_info() and info is not None
    assert info["port"] == puente.puerto and proto.PUERTO_POR_DEFECTO <= info["port"] <= proto.PUERTO_POR_DEFECTO + 10
    assert info["token"] == puente.token and len(info["token"]) >= 32 and info["pid"] == os.getpid()
    assert info["version"] and info["protocol"] == proto.PROTOCOLO
    assert puente.servidor.serverAddress().toString() == "127.0.0.1"
    assert ventana.puente.indicador.isVisible() and "Puente IA activo" in ventana.puente.indicador.text()
    ventana._puente_sesion = False
    ventana._aplicar_puente()
    assert proto.leer_info() is None and not proto.ruta_info().exists() and not ventana.puente.indicador.isVisible()
    assert ventana.encender_puente() and ventana.puente.token != info["token"]          # token nuevo por arranque


def test_la_preferencia_lo_prende_y_apaga_sin_reiniciar(ventana):
    from omnicad.ui.preferencias import DialogoPreferencias
    dlg = DialogoPreferencias(ventana.prefs)
    assert {"general/puente_agentes", "general/puente_codigo"} <= set(dlg.controles)
    assert ventana.prefs["general/puente_agentes"] is False                             # apagado por defecto
    dlg.controles["general/puente_agentes"].setChecked(True)
    dlg.aplicado.connect(ventana.aplicar_preferencias)
    dlg._aplicar()
    assert ventana.puente.activo and proto.leer_info() is not None
    dlg.controles["general/puente_agentes"].setChecked(False)
    dlg._aplicar()
    assert not ventana.puente.activo and proto.leer_info() is None
    dlg.deleteLater()


# ---------------------------------------------------------------- seguridad
def test_token_incorrecto_responde_unauthorized_y_cierra(puente):
    c = _cliente(puente)
    r = c.pedir("get_scene_info", token="no-es-el-token")
    assert r["ok"] is False and r["error_kind"] == "UNAUTHORIZED" and r["pistas"]
    c._esperar(lambda: c.s.state() == QAbstractSocket.SocketState.UnconnectedState, "el cierre")
    assert puente.conectados == 0


# ---------------------------------------------------------------- llamadas en vivo
def test_ping_status_create_box_y_undo_sobre_la_ventana(puente, ventana):
    c = _cliente(puente)
    try:
        assert c.pedir("ping")["result"]["pong"] is True
        assert puente.conectados == 1 and "Agente IA conectado" in puente.indicador.text()
        estado = c.pedir("status")["result"]
        assert estado["busy"] is False and estado["command_open"] is False and estado["modified"] is False
        assert estado["execute_code_allowed"] is False
        r = c.pedir("create_box", {"length": 20, "width": 10, "height": 5})
        assert r["ok"], r
        cuerpos = ventana.doc.estado_final.cuerpos
        assert len(cuerpos) == 1 and ventana.doc.modificado
        cid = next(iter(cuerpos))
        assert ventana.navegador.item(cid) is not None                   # el navegador de la ventana lo muestra
        assert "Agente IA: create_box" in ventana.timeline.estado.toolTip()
        escena = c.pedir("get_scene_info")["result"]
        assert [b["volume"] for b in escena["bodies"]] == [pytest.approx(1000.0)]
        imagen = c.pedir("get_viewport_image", {"width": 160, "height": 120})["result"]["image"]
        assert set(imagen) == {"png_base64", "width", "height"} and (imagen["width"], imagen["height"]) == (160, 120)
        assert base64.b64decode(imagen["png_base64"])[:8] == FIRMA_PNG
        r = c.pedir("undo")
        assert r["ok"] and not ventana.doc.estado_final.cuerpos and ventana.navegador.item(cid) is None
        assert c.pedir("herramienta_que_no_existe")["error_kind"] == "UNKNOWN_TOOL"
    finally:
        c.cerrar()
    c._esperar(lambda: puente.conectados == 0, "que el puente vea la desconexión")
    assert "Puente IA activo" in puente.indicador.text()


def test_app_busy_con_un_comando_abierto_o_un_boceto(puente, ventana):
    from omnicad.nucleo import geometria as geo
    from omnicad.restricciones import Boceto
    from omnicad.ui.comandos import CATALOGO
    c = _cliente(puente)
    try:
        panel = ventana.ejecutar_comando(CATALOGO["plano_desfase"]())
        assert panel is not None
        r = c.pedir("create_box", {"length": 10, "width": 10, "height": 10})
        assert r["error_kind"] == "APP_BUSY" and "comando" in r["mensaje"] and any("esperá" in p for p in r["pistas"])
        assert not ventana.doc.operaciones                                # no se aplicó nada
        assert c.pedir("get_scene_info")["ok"]                            # leer sí se puede
        assert c.pedir("status")["result"]["command_open"] is True
        panel.cancelar()
        QTest.qWait(10)
        ventana._iniciar_boceto(Boceto(), geo.Plano("XY"), {"op": None, "plano": "XY", "marco": None})
        r = c.pedir("undo")
        assert r["error_kind"] == "APP_BUSY" and "boceto" in r["mensaje"]
        ventana.modo_boceto.cancelar()
        assert c.pedir("create_box", {"length": 10, "width": 10, "height": 10})["ok"]
    finally:
        c.cerrar()


def test_new_y_open_document_con_cambios_sin_guardar(puente, ventana, tmp_path):
    from omnicad import api
    from omnicad.ejemplo import crear_documento_ejemplo
    ruta = tmp_path / "ejemplo.omnicad"
    api.Sesion(crear_documento_ejemplo()).guardar(ruta)
    c = _cliente(puente)
    try:
        assert c.pedir("create_box", {"length": 10, "width": 10, "height": 10})["ok"]
        antes = ventana.doc
        for tool, args in (("new_document", {"name": "Otro"}), ("open_document", {"path": str(ruta)})):
            r = c.pedir(tool, args)
            assert r["error_kind"] == "UNSAVED_CHANGES" and any("save_document" in p for p in r["pistas"])
            assert ventana.doc is antes and ventana.doc.estado_final.cuerpos     # no se descartó nada
        guardado = c.pedir("save_document", {"path": str(tmp_path / "caja.omnicad")})
        assert guardado["ok"] and not ventana.doc.modificado
        r = c.pedir("open_document", {"path": str(ruta)})
        assert r["ok"] and ventana.doc is not antes and ventana.doc.ruta == str(ruta)
        assert [b["id"] for b in r["result"]["bodies"]] == list(ventana.doc.estado_final.cuerpos)
        r = c.pedir("new_document", {"name": "Vacío"})
        assert r["ok"] and ventana.doc.nombre == "Vacío" and not ventana.doc.estado_final.cuerpos
        assert "Vacío" in ventana.windowTitle()
    finally:
        c.cerrar()


def test_execute_code_en_vivo_solo_con_su_preferencia(puente, ventana):
    c = _cliente(puente)
    try:
        r = c.pedir("execute_code", {"code": "result = 1 + 1"})
        assert r["error_kind"] == "LIVE_NOT_ALLOWED" and r["pistas"]
        ventana.prefs["general/puente_codigo"] = True
        r = c.pedir("execute_code", {"code": "result = len(doc.operaciones)"})
        assert r["ok"] and r["result"]["result"] == 0
    finally:
        ventana.prefs["general/puente_codigo"] = False
        c.cerrar()


def test_pedidos_mal_formados_no_tiran_la_app(puente):
    c = _cliente(puente)
    try:
        c.s.write(b"esto no es json\n")
        assert c.leer()["error_kind"] == "INVALID_REQUEST"
        assert c.pedir("ping")["ok"]                                     # la conexión sigue sirviendo
    finally:
        c.cerrar()


def test_app_y_puentes_usan_la_misma_carpeta_de_datos(monkeypatch, tmp_path):
    """En Linux la app guardaba en ~/OmniCAD y el puente en ~/.local/share/OmniCAD: ahora es una sola regla."""
    from pathlib import Path

    from omnicad import carpeta_datos
    from omnicad.io_archivos import puente_fusion
    for variable in ("LOCALAPPDATA", proto.VARIABLE_CARPETA, puente_fusion.VARIABLE_CARPETA):
        monkeypatch.delenv(variable, raising=False)
    monkeypatch.setattr(Path, "home", classmethod(lambda cls: tmp_path))
    assert carpeta_datos() == tmp_path / ".local" / "share" / "OmniCAD"           # Linux y macOS
    assert proto.carpeta_info() == puente_fusion.carpeta_info() == carpeta_datos()
    monkeypatch.setenv("LOCALAPPDATA", str(tmp_path / "local"))                   # Windows
    assert proto.carpeta_info() == puente_fusion.carpeta_info() == carpeta_datos() == tmp_path / "local" / "OmniCAD"
