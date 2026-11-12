"""Adaptador Qt: ganchos reversibles, vigilante y muestras únicamente al estar activo."""
import platform
import sys
import time
from collections import deque

from PySide6.QtCore import QEvent, QObject, QSize, Qt, QTimer, QUrl, qInstallMessageHandler
from PySide6.QtGui import QAction, QDesktopServices, QKeySequence
from PySide6.QtWidgets import (QAbstractButton, QApplication, QCheckBox, QComboBox, QDialog, QDialogButtonBox,
                               QFormLayout, QLabel, QLineEdit, QMenu, QPlainTextEdit, QPushButton, QToolButton,
                               QVBoxLayout)

from .. import VERSION
from .. import registro_uso as registro
from ..registro_uso.sistema import ram_total
from ..registro_uso.ganchos import error
from .iconos import icono


class _DialogoReporte(QDialog):
    def eventFilter(self, obj, evento):
        # QDialogButtonBox vuelve a elegir un botón por defecto al mostrarse.
        if evento.type() == QEvent.KeyPress and evento.key() in (Qt.Key_Return, Qt.Key_Enter):
            return True
        return super().eventFilter(obj, evento)


def _nombre_accion(accion, con_texto=True):
    """Clave de la QAction; si no tiene, su objectName; si tampoco, su texto (evita «sin_clave»).
    `con_texto=False` lo omite: el texto de un botón puede ser lo que la persona escribió o un nombre de archivo."""
    nombre = accion.property("clave") or accion.objectName()
    return nombre or (accion.text().replace("&", "").strip() if con_texto else "")


class RegistroVentana(QObject):
    def __init__(self, ventana):
        super().__init__(ventana)
        self.ventana = ventana
        self.preferencia = ventana.prefs["general/registro_uso"]
        self._encendido = False
        self._ultima_accion = ""
        self.herramienta_api = ""
        self.api_terminada = None
        self._anterior_excepcion = None
        self._anterior_qt = None
        self._barra = None
        self.reloj = QTimer(self, interval=50)
        self.reloj.timeout.connect(self._latido)
        self.indicador = QLabel("● REG", objectName="indicador_registro_uso")
        self.indicador.setToolTip("Registro local de uso activo. No se envía nada.")
        self.indicador.setParent(ventana)
        self.indicador.hide()
        nombre = "Reportar problema y sugerencia"
        self.boton = QPushButton("Reportar", objectName="marcar_problema")
        self.boton.setIcon(icono("reportar_problema"))
        self.boton.setIconSize(QSize(16, 16))
        self.boton.setToolTip(nombre)
        self.boton.setAccessibleName(nombre)
        self.boton.setStyleSheet("""
            QPushButton { padding: 3px 8px; border: 1px solid palette(mid); border-radius: 5px;
                          background: palette(button); color: palette(button-text); }
            QPushButton:hover { background: palette(light); border-color: palette(highlight); }
            QPushButton:pressed { background: palette(alternate-base); }
            QPushButton:focus { border-color: palette(highlight); }
        """)
        self.boton.clicked.connect(self._dialogo_marca)
        self.boton.setParent(ventana)
        self.boton.hide()
        self.accion = QAction(icono("reportar_problema"), nombre, ventana)
        self.accion.setToolTip(nombre)
        self.accion.setShortcut(QKeySequence("Ctrl+Shift+M"))
        self.accion.triggered.connect(self._dialogo_marca)
        ventana.addAction(self.accion)
        self.accion.setEnabled(False)

    def aplicar_ajustes(self, opciones):
        """Desde la API (MCP en vivo): escribe las preferencias y se las aplica a la ventana."""
        p = self.ventana.prefs
        for clave, valor in opciones.items():
            p[registro.CLAVES_PREFS[clave]] = valor
        self.aplicar_valores()
        return registro.activo.estado() if registro.activo else {"enabled": False, "session": None,
                                                                 "error": None, "dropped": 0}

    def aplicar_valores(self):
        """Preferencias › Registro de uso: los valores nuevos rigen al aceptar, sin reiniciar."""
        p = self.ventana.prefs
        guardados = {clave: p[clave_prefs] for clave, clave_prefs in registro.CLAVES_PREFS.items()}
        try:
            nuevos = registro.aplicar(guardados)
        except ValueError:                     # un .ini tocado a mano: se vuelve a fábrica, no se rompe la app
            nuevos = registro.aplicar(registro.FABRICA)
        r = registro.activo
        if r is not None:
            r.reajustar(nuevos)
        return nuevos

    def configurar(self, encendido):
        v = self.ventana
        datos = {"proyecto": getattr(v, "_proyecto_registro", None) or v.doc.ruta or v.doc.nombre,
                 "ventana": [v.width(), v.height()],
                 "ram_total": ram_total() if encendido and registro.activo is None else None,
                 "gpu": getattr(v.visor, "info_gl", "no disponible"),
                 "opengl": getattr(v.visor, "info_gl", "no disponible")}
        try:
            estado = registro.configurar(encendido, datos)
        except OSError as e:
            estado = {"enabled": False, "session": None, "error": type(e).__name__, "dropped": 0}
            self.ventana.mensaje(f"No se pudo activar el registro local: {e}", 10000)
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
        self._barra = v.statusBar()
        self._barra.addPermanentWidget(self.indicador)
        self._barra.addPermanentWidget(self.boton)
        self._barra.show()
        self.indicador.show()
        self.boton.show()
        self._anterior_excepcion = sys.excepthook
        sys.excepthook = self._excepcion
        self._anterior_qt = qInstallMessageHandler(self._mensaje_qt)
        QApplication.instance().installEventFilter(self)
        v.visor._cuadros_uso = deque(maxlen=6000)
        self._ultimo = self._muestra = time.perf_counter()
        self._rss, self._pausado = None, False
        self._duda = None
        self.reloj.start()

    def _detener(self):
        self.reloj.stop()
        if self._barra is not None:
            self._barra.removeWidget(self.indicador)
            self._barra.removeWidget(self.boton)
            self._barra.hide()
            self._barra = None
        self.indicador.hide()
        self.boton.hide()
        self.ventana.visor._cuadros_uso = None
        if sys.excepthook == self._excepcion and self._anterior_excepcion is not None:
            sys.excepthook = self._anterior_excepcion
        qInstallMessageHandler(self._anterior_qt)      # None vuelve al manejador de Qt
        self._anterior_qt = None
        app = QApplication.instance()
        if app is not None:
            app.removeEventFilter(self)

    def _excepcion(self, tipo, valor, tb):
        error(valor, origen="qt_slot", comando=self._comando())
        if self._anterior_excepcion is not None:
            self._anterior_excepcion(tipo, valor, tb)

    def _mensaje_qt(self, tipo, contexto, mensaje):
        if registro.activo is not None and tipo.value >= 1:
            registro.activo.emitir("error", {"origen": "qt", "categoria": tipo.name, "mensaje": mensaje,
                                           "linea": contexto.line})
        if self._anterior_qt:
            self._anterior_qt(tipo, contexto, mensaje)

    def _capturar_error(self):
        """La foto chica del visor que el registro pidió para el último error (modo detallado)."""
        r = registro.activo
        if r is None or r._captura_pendiente is None:
            return
        seq, r._captura_pendiente = r._captura_pendiente, None
        png = self.ventana.visor.captura_png(ancho=640)
        if not png:
            return
        try:
            r.escribir_captura(f"error_{r.id}_{seq}.png", png)
        except OSError:
            pass                                         # el error ya se registró; la captura es un extra

    def _comando(self):
        p = self.ventana.panel
        return p.comando.CLAVE if p is not None else ""

    def eventFilter(self, obj, evento):
        r = registro.activo
        if r is None:
            return False
        tipo = evento.type()
        if tipo == QEvent.Shortcut and isinstance(obj, QAction):
            clave = _nombre_accion(obj) or "sin_clave"
            self._ultima_accion = clave
            r.emitir("atajo", {"accion": clave})
        elif tipo == QEvent.MouseButtonPress:
            # Solo visor y botones: nunca se observa el teclado ni los campos de texto (chat incluido).
            if obj is not self.ventana.visor and not isinstance(obj, QAbstractButton):
                return False
            r.emitir("clic", {"objetivo": obj.objectName() or type(obj).__name__,
                              "clase": type(obj).__name__, "x": int(evento.position().x()) // 8,
                              "y": int(evento.position().y()) // 8})
            if isinstance(obj, QToolButton) and obj.defaultAction():
                clave = _nombre_accion(obj.defaultAction(), con_texto=False)
                if clave:
                    self._ultima_accion = clave
                    r.emitir("boton_cinta", {"accion": clave})
        elif tipo == QEvent.MouseButtonRelease and isinstance(obj, QMenu):
            a = obj.activeAction()
            if a is not None:
                clave = _nombre_accion(a) or obj.objectName() or "sin_clave"
                self._ultima_accion = clave
                r.emitir("menu_item", {"accion": clave, "etiqueta": a.text().replace("&", "")[:64]})
        return False

    def _latido(self):
        r = registro.activo
        if r is None:
            return
        if r.fallo:
            self.configurar(False)
            self.ventana.mensaje("Se detuvo el registro local por un error de escritura.", 10000)
            return
        self._capturar_error()
        if registro.toca_podar():
            registro.marcar_podar()
            registro.podar()
        pausado = r.disco_bajo()
        if pausado != self._pausado:
            self._pausado = pausado
            if pausado:
                self.ventana.mensaje("El registro de uso está pausado: queda poco espacio libre en disco.", 10000)
        ahora = time.perf_counter()
        herramienta = getattr(self, "herramienta_api", "")
        terminada = getattr(self, "api_terminada", None)
        if not herramienta and terminada is not None and terminada[1] > self._ultimo:
            herramienta = terminada[0]
        self.api_terminada = None  # El temporizador puede volver recién después del finally del puente.
        demora, self._ultimo = (ahora - self._ultimo - 0.05) * 1000, ahora
        comando = self._comando()
        if demora > 250:
            accion = f"api.{herramienta}" if herramienta else self._ultima_accion
            r.emitir("bloqueo_ui", {"duracion_ms": demora, "comando": comando, "accion": accion})
        p = self.ventana.panel
        cambio = getattr(p, "_uso_cambio", None)
        if cambio is not None and ahora - cambio > 20 and self._duda != cambio:
            r.emitir("dialogo_inactivo", {"comando": comando, "duracion_s": ahora - cambio})
            self._duda = cambio
        cada = registro.valores()["memoria_cada_s"]
        from .bench import memoria_mb
        try:
            rss = memoria_mb()[0] * 2**20
        except OSError:
            rss = None
        # menos ruido: se mide cada `memoria_cada_s`, o antes si la memoria se movió más de un 5 %
        salto = self._rss is None or rss is None or abs(rss - self._rss) > 0.05 * self._rss
        if not salto and ahora - self._muestra < cada:
            return
        self._muestra = ahora
        self._rss = rss
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
        d = _DialogoReporte(self.ventana)
        d.setWindowTitle("Reportar problema y sugerencia")
        d.resize(480, 350)
        l = QVBoxLayout(d)
        formulario = QFormLayout()
        tipo = QComboBox()
        tipo.addItems(["Problema", "Sugerencia"])
        titulo = QLineEdit(maxLength=2000)
        titulo.setPlaceholderText("Obligatorio para GitHub")
        formulario.addRow("Tipo:", tipo)
        formulario.addRow("Título:", titulo)
        l.addLayout(formulario)
        l.addWidget(QLabel("Nota (hasta 2000 caracteres; se guarda tal cual):"))
        nota = QPlainTextEdit()
        l.addWidget(nota)
        captura = QCheckBox("Adjuntar captura", objectName="adjuntar_captura")
        captura.setToolTip("Guarda un PNG del visor que puede mostrar el diseño; lo podés arrastrar al issue.")
        l.addWidget(captura)
        github = QCheckBox("Abrir issue en GitHub", objectName="abrir_issue_github")
        github.setToolTip("Abre un borrador en el navegador para que lo revises y lo envíes vos.")
        l.addWidget(github)
        botones = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        aceptar = botones.button(QDialogButtonBox.Ok)
        aceptar.setText("Aceptar")
        botones.button(QDialogButtonBox.Cancel).setText("Cancelar")
        for boton in botones.buttons():
            boton.setAutoDefault(False)
            boton.setDefault(False)
        botones.accepted.connect(d.accept)
        botones.rejected.connect(d.reject)
        l.addWidget(botones)
        for control in (d, tipo, captura, github, *botones.buttons()):
            control.installEventFilter(d)

        def validar():
            aceptar.setEnabled(not github.isChecked() or bool(titulo.text().strip()))

        def limitar_nota():
            texto = nota.toPlainText()
            if len(texto) > 2000:
                posicion = nota.textCursor().position()
                nota.setPlainText(texto[:2000])
                cursor = nota.textCursor()
                cursor.setPosition(min(posicion, nota.document().characterCount() - 1))
                nota.setTextCursor(cursor)

        github.toggled.connect(validar)
        titulo.textChanged.connect(validar)
        titulo.returnPressed.connect(aceptar.click)
        nota.textChanged.connect(limitar_nota)
        titulo.setFocus()
        if d.exec() != QDialog.Accepted:
            return
        r = registro.activo
        try:
            seq = self.marcar(nota.toPlainText(), captura.isChecked(), tipo=tipo.currentText(), titulo=titulo.text())
        except OSError as e:
            self.ventana.mensaje(f"No se pudo guardar la captura del reporte: {e}", 8000)
            return
        if seq is None:
            self.ventana.mensaje("No se pudo guardar el reporte local: revisá el estado del registro de uso.", 8000)
            return
        if github.isChecked():
            png = str(r.carpeta / f"marca_{r.id}_{seq}.png") if captura.isChecked() else None
            try:
                url = registro.url_issue(tipo.currentText(), titulo.text(), nota.toPlainText(),
                                         VERSION, platform.system(), png)
            except ValueError as e:
                self.ventana.mensaje(f"El reporte local quedó guardado. {e}", 8000)
                return
            if not QDesktopServices.openUrl(QUrl(url)):
                self.ventana.mensaje("El reporte local quedó guardado, pero no se pudo abrir el navegador.", 8000)

    def marcar(self, nota="", captura=False, label=None, *, tipo="Problema", titulo=""):
        r = registro.activo
        if r is None:
            return None
        datos = {"nota": nota, "captura": captura, "tipo": tipo, "titulo": titulo}
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
