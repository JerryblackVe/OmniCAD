"""Adaptador Qt: ganchos reversibles, vigilante y muestras únicamente al estar activo."""
import sys
import time
from collections import deque

from PySide6.QtCore import QEvent, QObject, QTimer, qInstallMessageHandler
from PySide6.QtGui import QAction, QKeySequence
from PySide6.QtWidgets import (QAbstractButton, QApplication, QCheckBox, QDialog, QDialogButtonBox, QLabel,
                               QLineEdit, QMenu, QPushButton, QToolButton, QVBoxLayout)

from .. import registro_uso as registro
from ..registro_uso.sistema import ram_total
from ..registro_uso.ganchos import error


class RegistroVentana(QObject):
    def __init__(self, ventana):
        super().__init__(ventana)
        self.ventana = ventana
        self.preferencia = ventana.prefs["general/registro_uso"]
        self._encendido = False
        self._ultima_accion = ""
        self.reloj = QTimer(self, interval=50)
        self.reloj.timeout.connect(self._latido)
        self.indicador = QLabel("● REG", objectName="indicador_registro_uso")
        self.indicador.setToolTip("Registro local de uso activo. No se envía nada.")
        ventana.statusBar().addPermanentWidget(self.indicador)
        self.indicador.hide()
        self.boton = QPushButton("Marcar problema", objectName="marcar_problema")
        self.boton.clicked.connect(self._dialogo_marca)
        ventana.statusBar().addPermanentWidget(self.boton)
        self.boton.hide()
        self.accion = QAction("Marcar problema", ventana)
        self.accion.setShortcut(QKeySequence("Ctrl+Shift+M"))
        self.accion.triggered.connect(self._dialogo_marca)
        ventana.addAction(self.accion)
        self.accion.setEnabled(False)

    def configurar(self, encendido):
        v = self.ventana
        datos = {"proyecto": getattr(v, "_proyecto_registro", None) or v.doc.ruta or v.doc.nombre,
                 "ventana": [v.width(), v.height()],
                 "ram_total": ram_total() if encendido and registro.activo is None else None,
                 "gpu": getattr(v.visor, "info_gl", "no disponible"),
                 "opengl": getattr(v.visor, "info_gl", "no disponible")}
        estado = registro.configurar(encendido, datos)
        self.indicador.setVisible(estado["enabled"])
        self.boton.setVisible(estado["enabled"])
        self.accion.setEnabled(estado["enabled"])
        if estado["enabled"] != self._encendido:
            self._encendido = estado["enabled"]
            if self._encendido:
                self._iniciar()
            else:
                self._detener()
        return estado

    def _iniciar(self):
        v = self.ventana
        self._anterior_excepcion = sys.excepthook
        sys.excepthook = self._excepcion
        self._anterior_qt = qInstallMessageHandler(self._mensaje_qt)
        QApplication.instance().installEventFilter(self)
        v.visor._cuadros_uso = deque(maxlen=6000)
        self._ultimo = self._muestra = time.perf_counter()
        self._duda = None
        self.reloj.start()

    def _detener(self):
        self.reloj.stop()
        self.ventana.visor._cuadros_uso = None
        if hasattr(self, "_anterior_excepcion"):
            if sys.excepthook == self._excepcion:
                sys.excepthook = self._anterior_excepcion
            qInstallMessageHandler(self._anterior_qt)
        app = QApplication.instance()
        if app is not None:
            app.removeEventFilter(self)

    def _excepcion(self, tipo, valor, tb):
        error(valor, origen="qt_slot", comando=self._comando())
        self._anterior_excepcion(tipo, valor, tb)

    def _mensaje_qt(self, tipo, contexto, mensaje):
        if registro.activo is not None and tipo.value >= 1:
            registro.activo.emitir("error", {"origen": "qt", "categoria": tipo.name, "mensaje": mensaje,
                                           "linea": contexto.line})
        if self._anterior_qt:
            self._anterior_qt(tipo, contexto, mensaje)

    def _comando(self):
        p = self.ventana.panel
        return p.comando.CLAVE if p is not None else ""

    def eventFilter(self, obj, evento):
        r = registro.activo
        if r is None:
            return False
        tipo = evento.type()
        if tipo == QEvent.Shortcut and isinstance(obj, QAction):
            clave = obj.property("clave") or obj.objectName() or "sin_clave"
            self._ultima_accion = clave
            r.emitir("atajo", {"accion": clave})
        elif tipo == QEvent.MouseButtonPress:
            # Solo visor y botones: nunca se observa el teclado ni los campos de texto (chat incluido).
            if obj is not self.ventana.visor and not isinstance(obj, QAbstractButton):
                return False
            r.emitir("clic", {"objetivo": id(obj), "x": int(evento.position().x()) // 8,
                               "y": int(evento.position().y()) // 8})
            if isinstance(obj, QToolButton) and obj.defaultAction():
                clave = obj.defaultAction().property("clave")
                if clave:
                    self._ultima_accion = clave
                    r.emitir("boton_cinta", {"accion": clave})
        elif tipo == QEvent.MouseButtonRelease and isinstance(obj, QMenu):
            a = obj.activeAction()
            if a is not None:
                clave = a.property("clave") or obj.objectName() or "sin_clave"
                self._ultima_accion = clave
                r.emitir("menu_item", {"accion": clave, "etiqueta": a.text()})
        return False

    def _latido(self):
        r = registro.activo
        if r is None:
            return
        if r.fallo:
            self.configurar(False)
            self.ventana.mensaje("Se detuvo el registro local por un error de escritura.", 10000)
            return
        ahora = time.perf_counter()
        demora, self._ultimo = (ahora - self._ultimo - 0.05) * 1000, ahora
        comando = self._comando()
        if demora > 250:
            r.emitir("bloqueo_ui", {"duracion_ms": demora, "comando": comando, "accion": self._ultima_accion})
        p = self.ventana.panel
        cambio = getattr(p, "_uso_cambio", None)
        if cambio is not None and ahora - cambio > 20 and self._duda != cambio:
            r.emitir("dialogo_inactivo", {"comando": comando, "duracion_s": ahora - cambio})
            self._duda = cambio
        if ahora - self._muestra < 5:
            return
        self._muestra = ahora
        from .bench import memoria_mb
        try:
            rss = memoria_mb()[0] * 2**20
        except OSError:
            rss = None
        doc = self.ventana.doc
        formas = {id(c.forma) for estado in doc._estados for c in estado.cuerpos.values()}
        r.emitir("memoria", {"rss": rss, "objetos_occ": len(formas), "cuerpos": len(doc.estado_final.cuerpos)})
        cuadros = self.ventana.visor._cuadros_uso
        if cuadros:
            ms = sorted(cuadros)
            cuadros.clear()
            fps = [1000 / max(m, 0.001) for m in ms]          # ms ascendente → FPS descendente
            r.emitir("visor_cuadros", {"fps_promedio": sum(fps) / len(fps),
                "fps_p95": fps[min(len(fps) - 1, int(len(fps) * 0.05))],
                "fps_minimo": fps[-1], "cuadros": len(fps),
                "promedio_ms": sum(ms) / len(ms), "p95_ms": ms[min(len(ms) - 1, int(len(ms) * 0.95))]})

    def _dialogo_marca(self):
        if registro.activo is None:
            return
        d = QDialog(self.ventana)
        d.setWindowTitle("Marcar problema")
        l = QVBoxLayout(d)
        l.addWidget(QLabel("Nota opcional (solo se guarda su longitud):"))
        nota = QLineEdit(maxLength=160)
        l.addWidget(nota)
        captura = QCheckBox("Guardar también una captura del visor (puede mostrar el diseño)")
        l.addWidget(captura)
        botones = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        botones.accepted.connect(d.accept)
        botones.rejected.connect(d.reject)
        l.addWidget(botones)
        if d.exec() == QDialog.Accepted:
            try:
                self.marcar(nota.text(), captura.isChecked())
            except OSError as e:
                self.ventana.mensaje(f"No se pudo guardar la captura del marcador: {e}", 8000)

    def marcar(self, nota="", captura=False, label=None):
        r = registro.activo
        if r is None:
            return None
        datos = {"nota": nota, "captura": captura}
        if label:
            datos["label"] = label
        seq = r.emitir("marca", datos)
        if captura and seq is not None:
            png = self.ventana.visor.captura_png()
            if not png:
                raise OSError("No se pudo capturar el visor.")
            r._podar(len(png))
            ruta = r.carpeta / f"marca_{r.id}_{seq}.png"
            ruta.write_bytes(png)
        return seq
