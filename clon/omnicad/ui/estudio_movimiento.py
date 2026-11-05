# -*- coding: utf-8 -*-
"""ENSAMBLAR › Estudio de movimiento [Motion Study reference]: un panel con TODAS las uniones (nombre, grado de
libertad y valor), botones de reproducir hacia atrás y hacia adelante o paso a paso, el modo (en un sentido, ida y
vuelta o bucle) y la velocidad. Mueve solo el dibujo de los cuerpos (`visor.transformaciones`): no recalcula ni cambia
el documento. Las cuentas están en `timeline/ops_ensamblar.poses_de_estudio`."""
import time

from PySide6.QtCore import Qt, QTimer
from PySide6.QtWidgets import (QCheckBox, QComboBox, QDialog, QHBoxLayout, QLabel, QPushButton,
                               QScrollArea, QSlider, QVBoxLayout, QWidget)

from ..nucleo import geometria as geo
from ..timeline.operaciones import Contexto, ErrorOperacion
from ..timeline.parametros import ErrorExpresion
from ..timeline.ops_ensamblar import MOVIMIENTOS, poses_de_estudio, valores_de_estudio
from .formulario import NumeroDecimal

MODOS = {"una_vez": "En un sentido", "ida_vuelta": "Ida y vuelta", "bucle": "Bucle"}
NOMBRES = {"giro": "Giro", "giro2": "Giro 2 (cabeceo)", "giro3": "Giro 3 (guiñada)", "desliz": "Deslizamiento",
           "desliz2": "Deslizamiento 2"}
SEGUNDOS = 4.0              # lo que tarda un recorrido entero a velocidad 1×
PASOS = 20                  # «paso a paso»: un recorrido son 20 pasos
VELOCIDADES = (0.25, 0.5, 1.0, 2.0, 4.0)
MARCAS = 1000


def fase_de_tiempo(t, modo):
    """(fase de 0 a 1 del recorrido, terminó) después de `t` recorridos enteros según el modo: «una_vez» llega a
    1 y se queda, «ida_vuelta» llega a 1 y vuelve a 0, «bucle» repite de 0 a 1 sin parar."""
    if modo == "ida_vuelta":
        u = min(t, 2.0)
        return (u if u <= 1.0 else 2.0 - u), t >= 2.0
    if modo == "bucle":
        return t % 1.0, False
    return min(t, 1.0), t >= 1.0


def tamano_modelo(estado):
    """Largo de la diagonal del cuerpo más grande: el recorrido de un deslizamiento sin límites."""
    largos = []
    for c in estado.cuerpos.values():
        a, b = geo.caja_envolvente(c.forma) if getattr(c, "tipo", "solido") != "malla" else c.forma.caja()
        largos.append(sum((x - y) ** 2 for x, y in zip(a, b, strict=True)) ** 0.5)
    return max(largos, default=50.0) or 50.0


def rango(doc, uid, clave, tam):
    """(mínimo, máximo) que recorre un movimiento: sus límites si los tiene y, si no, 0 a 360° o 0 a `tam` mm."""
    try:
        mn, mx = doc.operacion(uid).limites(Contexto(doc.parametros.valores()), clave)
    except (ErrorExpresion, ErrorOperacion):         # un límite que no se puede calcular no impide abrir el panel
        mn = mx = None
    base = (0.0, 360.0) if clave.startswith("giro") else (0.0, tam)
    mn, mx = (base[0] if mn is None else mn), (base[1] if mx is None else mx)
    return (mn, mx) if mx > mn else (mn, mn + 1.0)


def aplicar_poses(ventana, poses):
    ventana.visor.transformaciones = poses
    ventana.visor.update()


class PanelEstudioMovimiento(QDialog):
    """Panel del estudio de movimiento. Una fila por movimiento de cada unión: casilla «Animar», valor (con deslizador)
    y su nombre. Las uniones que sigue un vínculo muestran el valor que les llega y no se tocan."""

    def __init__(self, ventana):
        super().__init__(ventana)
        self.setWindowTitle("Estudio de movimiento")
        self.setWindowFlag(Qt.Tool, True)
        self.ventana = ventana
        self.doc = ventana.doc
        self.estado = self.doc.estado_final
        tam = tamano_modelo(self.estado)
        self.filas = []
        self.setMinimumWidth(330)
        raiz = QVBoxLayout(self)
        cuerpo = QWidget()
        lista = QVBoxLayout(cuerpo)
        lista.setContentsMargins(0, 0, 0, 0)
        for uid, u in self.estado.uniones.items():
            giros, desliz = MOVIMIENTOS[u["tipo"]]
            for clave in giros + desliz:
                lista.addWidget(self._fila(uid, u, clave, tam))
        lista.addStretch(1)
        marco = QScrollArea()
        marco.setWidgetResizable(True)
        marco.setWidget(cuerpo)
        marco.setMinimumHeight(110)
        marco.setMaximumHeight(230)
        raiz.addWidget(marco)

        botones = QHBoxLayout()
        self.b_atras = self._boton("⏪", "Reproducir hacia atrás", lambda: self.reproducir(-1))
        self.b_paso_atras = self._boton("◀", "Un paso hacia atrás", lambda: self.paso(-1))
        self.b_parar = self._boton("■", "Detener", self.parar)
        self.b_paso = self._boton("▶", "Un paso hacia adelante", lambda: self.paso(1))
        self.b_adelante = self._boton("⏩", "Reproducir hacia adelante", lambda: self.reproducir(1))
        for b in (self.b_atras, self.b_paso_atras, self.b_parar, self.b_paso, self.b_adelante):
            botones.addWidget(b)
        raiz.addLayout(botones)

        ajustes = QHBoxLayout()
        ajustes.addWidget(QLabel("Modo"))
        self.modo = QComboBox()
        for clave, texto in MODOS.items():
            self.modo.addItem(texto, clave)
        ajustes.addWidget(self.modo, 1)
        raiz.addLayout(ajustes)
        velocidad = QHBoxLayout()
        velocidad.addWidget(QLabel("Velocidad"))
        self.velocidad = QSlider(Qt.Horizontal, minimum=0, maximum=len(VELOCIDADES) - 1, value=2)
        self.velocidad.setAccessibleName("Velocidad de reproducción")
        self.etiqueta_velocidad = QLabel("1×")
        self.velocidad.valueChanged.connect(lambda i: self.etiqueta_velocidad.setText(f"{VELOCIDADES[i]:g}×"))
        velocidad.addWidget(self.velocidad, 1)
        velocidad.addWidget(self.etiqueta_velocidad)
        raiz.addLayout(velocidad)
        cerrar = QPushButton("Cerrar")
        cerrar.clicked.connect(self.close)
        raiz.addWidget(cerrar)

        self._timer = QTimer(self, interval=33)
        self._timer.timeout.connect(self._tick)
        self._dir, self._t0, self._fase0 = 1, 0.0, 0.0

    # ------------------------------------------------------------ armado
    @staticmethod
    def _boton(texto, ayuda, accion):
        b = QPushButton(texto, toolTip=ayuda)
        b.setAccessibleName(ayuda)
        b.clicked.connect(lambda _=False: accion())
        return b

    def _fila(self, uid, u, clave, tam):
        mn, mx = rango(self.doc, uid, clave, tam)
        gira = clave.startswith("giro")
        sigue = bool(u.get("vinculo") and u["vinculo"]["clave2"] == clave)
        fila = QWidget()
        caja = QHBoxLayout(fila)
        caja.setContentsMargins(0, 0, 0, 0)
        marca = QCheckBox(f"{u['nombre']} · {NOMBRES[clave]}")
        marca.setChecked(not sigue)
        marca.setEnabled(not sigue)
        marca.setToolTip("Anima este movimiento al reproducir" + (" (lo mueve un vínculo)" if sigue else ""))
        spin = NumeroDecimal(decimals=2, minimum=min(mn, u["valores"].get(clave, 0.0)) - 1e-9,
                              maximum=max(mx, u["valores"].get(clave, 0.0)) + 1e-9, suffix=" °" if gira else " mm",
                              value=u["valores"].get(clave, 0.0))
        spin.setAccessibleName(f"Valor de {u['nombre']} · {NOMBRES[clave]}")
        spin.setKeyboardTracking(False)                      # el valor vale al dar Enter o salir del campo, no tecla a tecla
        spin.setEnabled(not sigue)
        marcha = QSlider(Qt.Horizontal, minimum=0, maximum=MARCAS, enabled=not sigue)
        marcha.setValue(self._marca(spin.value(), mn, mx))
        caja.addWidget(marca, 2)
        caja.addWidget(marcha, 2)
        caja.addWidget(spin, 1)
        datos = {"union": uid, "clave": clave, "rango": (mn, mx), "marca": marca, "spin": spin, "deslizador": marcha,
                 "sigue": sigue}
        self.filas.append(datos)
        spin.valueChanged.connect(lambda _v, d=datos: self._desde_valor(d))
        marcha.valueChanged.connect(lambda i, d=datos: self._desde_deslizador(d, i))
        return fila

    @staticmethod
    def _marca(valor, mn, mx):
        return round(max(0.0, min(1.0, (valor - mn) / (mx - mn))) * MARCAS)

    # ------------------------------------------------------------ valores
    def _poner(self, d, valor):
        """Escribe el valor en el campo y el deslizador de la fila sin disparar sus señales."""
        mn, mx = d["rango"]
        for w, v in ((d["spin"], valor), (d["deslizador"], self._marca(valor, mn, mx))):
            w.blockSignals(True)
            w.setValue(v)
            w.blockSignals(False)

    def _desde_valor(self, d):
        self._poner(d, d["spin"].value())
        self.aplicar()

    def _desde_deslizador(self, d, i):
        mn, mx = d["rango"]
        self._poner(d, mn + (mx - mn) * i / MARCAS)
        self.aplicar()

    def valores(self):
        """{unión: {movimiento: valor}} de las filas que se mueven a mano o por reproducción."""
        salida = {}
        for d in self.filas:
            if not d["sigue"]:
                salida.setdefault(d["union"], {})[d["clave"]] = d["spin"].value()
        return salida

    def set_valor(self, uid, clave, valor):
        d = next(f for f in self.filas if f["union"] == uid and f["clave"] == clave)
        d["spin"].setValue(valor)

    def aplicar(self):
        """Dibuja el mecanismo con los valores de las filas y muestra el valor que les llega a las que sigue un vínculo."""
        if self.doc.estado_final is not self.estado:      # el modelo cambió con el panel abierto: sus valores ya no valen
            self.close()
            return
        pedidos = self.valores()
        for d, v in ((d, valores_de_estudio(self.estado, pedidos)[d["union"]][d["clave"]])
                     for d in self.filas if d["sigue"]):
            self._poner(d, v)
        aplicar_poses(self.ventana, poses_de_estudio(self.estado, pedidos))

    # ------------------------------------------------------------ reproducción
    def _animadas(self):
        return [d for d in self.filas if d["marca"].isChecked() and not d["sigue"]]

    def _poner_fase(self, fase):
        for d in self._animadas():
            mn, mx = d["rango"]
            self._poner(d, mn + (mx - mn) * fase)
        self.aplicar()

    def reproducir(self, direccion):
        if not self._animadas():
            return
        self._dir, self._t0 = direccion, time.perf_counter()
        self._timer.start()

    def parar(self):
        self._timer.stop()

    @property
    def reproduciendo(self):
        return self._timer.isActive()

    def _tick(self):
        t = (time.perf_counter() - self._t0) * VELOCIDADES[self.velocidad.value()] / SEGUNDOS
        fase, fin = fase_de_tiempo(t, self.modo.currentData())
        self._poner_fase(fase if self._dir > 0 else 1.0 - fase)
        if fin:
            self.parar()

    def paso(self, direccion):
        """Un paso (el 5 % del recorrido) de cada movimiento animado, sin salirse de su rango."""
        self.parar()
        for d in self._animadas():
            mn, mx = d["rango"]
            v = d["spin"].value() + direccion * (mx - mn) / PASOS
            self._poner(d, max(mn, min(mx, v)))
        self.aplicar()

    # ------------------------------------------------------------ cierre
    def hideEvent(self, e):            # cerrar, la X y Esc: el dibujo vuelve a como está el modelo
        self.parar()
        aplicar_poses(self.ventana, {})
        super().hideEvent(e)


def alternar_animacion_vinculo(ventana, v, ctx):
    """«Animar» del vínculo de movimiento: recorre la unión 1 de ida y vuelta y la unión 2 la sigue con la relación
    del diálogo (aunque el vínculo todavía no esté creado). Una segunda llamada la detiene. Devuelve si quedó andando."""
    timer = getattr(ventana, "_t_vinculo", None)
    if timer is not None and timer.isActive():
        timer.stop()
        aplicar_poses(ventana, {})
        return False
    estado, doc = ctx.doc.estado_final, ctx.doc
    u1, u2 = estado.uniones.get(v.get("union1")), estado.uniones.get(v.get("union2"))
    if not u1 or not u2:
        return False
    from ..timeline.ops_ensamblar import _clave_movimiento
    c1, c2 = _clave_movimiento(u1, v.get("mov1")), _clave_movimiento(u2, v.get("mov2"))
    if v["union1"] == v["union2"] and c1 == c2:               # la misma unión: dos movimientos distintos de ella
        return False
    factor = ctx.evaluar(v.get("factor") or "1", "escalar") * (-1 if v.get("invertir") else 1)
    mn, mx = rango(doc, v["union1"], c1, tamano_modelo(estado))
    inicio = time.perf_counter()

    def paso():
        fase, _fin = fase_de_tiempo((time.perf_counter() - inicio) / SEGUNDOS * 2.0 % 2.0, "ida_vuelta")
        x = mn + (mx - mn) * fase
        pedidos = {v["union1"]: {c1: x}}
        pedidos.setdefault(v["union2"], {})[c2] = x * factor
        aplicar_poses(ventana, poses_de_estudio(estado, pedidos))

    if timer is None:
        timer = ventana._t_vinculo = QTimer(ventana, interval=33)
        timer.timeout.connect(lambda: ventana._paso_vinculo())
    ventana._paso_vinculo = paso
    timer.start()
    return True
