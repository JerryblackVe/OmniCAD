# -*- coding: utf-8 -*-
"""B-16: execute_code en vivo no congela la ventana. El vigía del plazo consulta un latido opcional cada
~0,1 s (en vivo: un diálogo modal con Cancelar que procesa eventos de Qt); si el latido pide cancelar, el
código se corta con CODE_CANCELLED y el documento vuelve a como estaba. Limitación aceptada: una llamada
interna larga (un recálculo) no se interrumpe a la mitad; el corte llega cuando vuelve al código del agente."""
import json
import os
import time

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtCore import QSettings, QTimer  # noqa: E402
from PySide6.QtNetwork import QAbstractSocket, QHostAddress, QTcpSocket  # noqa: E402
from PySide6.QtTest import QTest  # noqa: E402
from PySide6.QtWidgets import QApplication, QProgressDialog  # noqa: E402

from omnicad import api  # noqa: E402
from omnicad.api import protocolo_puente as proto  # noqa: E402

BUCLE = "while True:\n    llamar('create_box', {'length': 1, 'width': 1, 'height': 1})"


@pytest.fixture
def s():
    return api.Sesion()


def _foto(doc):
    return ([(o.id, o.nombre) for o in doc.operaciones], list(doc.estado_final.cuerpos))


# ---------------------------------------------------------------- sin Qt: el latido del vigía
def test_latido_que_cancela_corta_revierte_y_respeta_el_intervalo(s):
    antes = _foto(s.doc)
    tiempos, llamadas = [], [0]

    def latido():
        tiempos.append(time.monotonic())
        llamadas[0] += 1
        return llamadas[0] >= 3                      # cancelar a la 3ª consulta

    s.latido = latido
    r = api.llamar(s, "execute_code", {"code": BUCLE, "timeout": 30})
    assert r["ok"] is False and r["error_kind"] == "CODE_CANCELLED"
    assert "canceló" in r["mensaje"] and any("no hace falta deshacer" in p for p in r["pistas"])
    assert _foto(s.doc) == antes and not s.doc.modificado       # el documento volvió atrás
    assert len(tiempos) >= 3
    assert all(b - a >= 0.095 for a, b in zip(tiempos, tiempos[1:], strict=False)), \
        "el latido se llamó en cada línea"


def test_sin_latido_o_con_latido_tranquilo_se_comporta_como_hoy(s):
    r = api.llamar(s, "execute_code", {"code": "while True:\n    pass", "timeout": 0.3})
    assert r["error_kind"] == "CODE_TIMEOUT"                      # sin latido: igual que siempre
    s.latido = lambda: False                                     # latido que nunca cancela: termina normal
    r = api.llamar(s, "execute_code", {"code": "result = 41 + 1", "timeout": 5})
    assert r["ok"] and r["result"]["result"] == 42


# ---------------------------------------------------------------- con el puente en vivo
@pytest.fixture(scope="module")
def app_qt():
    return QApplication.instance() or QApplication([])


@pytest.fixture(scope="module")
def ventana(app_qt, tmp_path_factory):
    from omnicad.ui.preferencias import Preferencias
    from omnicad.ui.ventana import VentanaPrincipal
    carpeta = tmp_path_factory.mktemp("b16")
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
    from omnicad.timeline.documento import Documento
    ventana.set_documento(Documento())
    assert ventana.encender_puente()
    yield ventana.puente
    ventana._puente_sesion = False
    ventana._aplicar_puente()


class Cliente:
    """Cliente de líneas JSON con QTcpSocket: espera procesando eventos (QTest.qWait), nunca bloqueando."""

    def __init__(self, puerto, token):
        self.token, self.buffer = token, b""
        self.s = QTcpSocket()
        self.s.connectToHost(QHostAddress(QHostAddress.SpecialAddress.LocalHost), puerto)
        self._esperar(lambda: self.s.state() == QAbstractSocket.SocketState.ConnectedState, "conectar")

    def _esperar(self, condicion, que, segundos=20):
        limite = time.time() + segundos
        while not condicion():
            assert time.time() < limite, f"tiempo agotado esperando {que}"
            QTest.qWait(5)

    def enviar(self, ident, tool, args=None):
        self.s.write(proto.linea({"id": ident, "token": self.token, "tool": tool, "args": args or {}}))
        self.s.flush()

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


def test_execute_code_en_vivo_dialogo_cancela_y_la_cola_espera(puente, ventana):
    ventana.prefs["general/puente_codigo"] = True
    c = _cliente(puente)
    visto = {}

    def durante():
        dlg = QApplication.activeModalWidget()
        visto["es_dialogo"] = isinstance(dlg, QProgressDialog)
        visto["texto"] = dlg.labelText() if dlg is not None else ""
        # Un segundo pedido DURANTE la ejecución: tiene que quedar en la cola y atenderse después.
        c.enviar(2, "create_box", {"length": 4, "width": 4, "height": 4})
        dlg.cancel()

    try:
        QTimer.singleShot(300, durante)                  # dispara adentro del latido (procesa eventos de Qt)
        c.enviar(1, "execute_code", {"code": BUCLE, "timeout": 8})
        r1 = c.leer("la respuesta de execute_code")
        assert r1["id"] == 1 and r1["error_kind"] == "CODE_CANCELLED"
        r2 = c.leer("la respuesta de create_box")
        assert r2["id"] == 2 and r2["ok"]
        assert visto["es_dialogo"] and "código del agente" in visto["texto"]
        # El bucle se revirtió y el create_box (pedido 2) quedó como único paso: se atendió DESPUÉS.
        assert len(ventana.doc.operaciones) == 1 and len(ventana.doc.estado_final.cuerpos) == 1
    finally:
        ventana.prefs["general/puente_codigo"] = False
        c.cerrar()
