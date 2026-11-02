# -*- coding: utf-8 -*-
"""INSPECCIONAR › Mapa de desviación (F10 y SC13): pinta un cuerpo según cuánto se aparta de otro, con la escala, el mínimo,
el máximo y el valor bajo el cursor. El cálculo vive en `nucleo/comparar_malla.py`; la herramienta `compare_to_mesh` da los
mismos números a un agente."""
import numpy as np
from PySide6.QtCore import QEvent, QObject, QPointF, QRectF, Qt
from PySide6.QtGui import QColor, QLinearGradient, QPainter
from PySide6.QtWidgets import QLabel, QVBoxLayout, QWidget

from ...nucleo import comparar_malla as cm
from ...timeline.parametros import LONGITUD
from .. import analisis_vista
from ..comando import ErrorComando, Expresion, Info, Personalizado, Seleccion
from ..visor3d import rayo_triangulos
from . import registrar
from .inspeccionar import _Analisis, _hits_cuerpos, _mm

_CAPA = "desviacion_cursor"


def _qcolor(c):
    return QColor.fromRgbF(*c)


class _Escala(QWidget):
    """La escala de colores del mapa: azul falta, de verde a amarillo dentro de la tolerancia, rojo sobra."""
    ALTO = 34

    def __init__(self):
        super().__init__()
        self.setFixedHeight(self.ALTO)
        self.tolerancia = 0.1

    def paintEvent(self, _e):
        azul, verde, amarillo, rojo = (_qcolor(c) for c in cm.ESCALA)
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        ancho = float(self.width())
        barra = QRectF(0, 0, ancho, 14)
        g = QLinearGradient(QPointF(0, 0), QPointF(ancho, 0))
        for t, c in ((0.0, azul), (0.1999, azul), (0.2, amarillo), (0.5, verde), (0.8, amarillo), (0.8001, rojo), (1.0, rojo)):
            g.setColorAt(t, c)
        p.fillRect(barra, g)
        p.setPen(self.palette().windowText().color())
        for t, texto, alineado in ((0.2, _mm(-self.tolerancia), Qt.AlignLeft), (0.5, "0", Qt.AlignHCenter),
                                   (0.8, _mm(self.tolerancia), Qt.AlignRight)):
            caja = QRectF(ancho * t - 60, 16, 120, 16)
            if alineado == Qt.AlignLeft:
                caja = QRectF(ancho * t, 16, 120, 16)
            elif alineado == Qt.AlignRight:
                caja = QRectF(ancho * t - 120, 16, 120, 16)
            p.drawText(caja, int(alineado | Qt.AlignVCenter), texto)


class _Sonda(QObject):
    """Mira el ratón sobre el visor y dice cuánto vale el mapa en el punto que está bajo el cursor."""

    def __init__(self, visor, comando):
        super().__init__(visor)
        self.visor, self.comando = visor, comando
        visor.setMouseTracking(True)
        visor._hover_ent = None
        visor.installEventFilter(self)

    def eventFilter(self, _obj, e):
        if e.type() == QEvent.MouseMove and not e.buttons():
            self.comando.sondear(self.visor, e.position())
            return self.comando.pintado()               # con el mapa, el resalte bajo el cursor taparía los colores
        if e.type() == QEvent.Leave:
            self.comando.sondear(self.visor, None)
        return False


class MapaDesviacion(_Analisis):
    CLAVE, TITULO, ICONO, TIPO_ANALISIS = "mapa_desviacion", "Mapa de desviación", "mapa_desviacion", "desviacion"
    AYUDA = ("Pinta un cuerpo según cuánto se aparta de otro: un sólido contra su malla, o una versión vieja contra una nueva. "
             "La referencia no se dibuja mientras se mira el mapa: coincidiría con el cuerpo.")

    def __init__(self):
        super().__init__()
        self._tris, self._valores, self._sonda, self._cursor, self._panel = None, None, None, None, None

    def preparar_panel(self, panel):
        self._panel = panel

    def campos(self, ctx):
        return [Seleccion("cuerpos", "Cuerpo", {"cuerpo"}, sin_resalte=True),
                Seleccion("referencia", "Referencia", {"cuerpo"}, sin_resalte=True),
                Expresion("tolerancia", "Tolerancia", "0.1 mm", ayuda="Lo que pasa de acá se pinta de rojo (sobra) o azul (falta)."),
                Personalizado("escala", "", self._crear_escala, ancho_completo=True),
                Info("extremos", "", self._extremos),
                Personalizado("cursor", "", self._crear_cursor, ancho_completo=True)]

    def _crear_escala(self, _panel):
        self._escala = _Escala()
        return self._escala

    def _crear_cursor(self, _panel):
        caja = QWidget()
        marco = QVBoxLayout(caja)
        marco.setContentsMargins(0, 0, 0, 0)
        self._cursor = QLabel("Pasá el cursor por la pieza para ver su valor.", wordWrap=True)
        marco.addWidget(self._cursor)
        return caja

    def _extremos(self, _v, _ctx):
        if self._valores is None or not len(self._valores):
            return "Elegí el cuerpo y la referencia."
        return f"Mínimo {_mm(self._valores.min())} · Máximo {_mm(self._valores.max())}"

    def params(self, v, ctx):
        cuerpo, referencia = v.get("cuerpos") or [], v.get("referencia") or []
        return {"cuerpos": [h["ref"]["cuerpo"] for h in cuerpo], "referencia": referencia[0]["ref"]["cuerpo"] if referencia else None,
                "tolerancia": ctx.evaluar(v["tolerancia"], LONGITUD)}

    def desde_params(self, p, ctx):
        return {**super().desde_params(p, ctx), "referencia": _hits_cuerpos([p["referencia"]], ctx) if p.get("referencia") else [],
                "tolerancia": f"{p.get('tolerancia', 0.1):g} mm"}

    def _listo(self, v):
        return bool(v.get("cuerpos") and v.get("referencia"))

    def construir(self, v, ctx):
        if not self._listo(v):
            raise ErrorComando("Elegí el cuerpo y la referencia.")
        if v["cuerpos"][0]["ref"]["cuerpo"] == v["referencia"][0]["ref"]["cuerpo"]:
            raise ErrorComando("El cuerpo y la referencia son el mismo.")
        if not ctx.evaluar(v["tolerancia"], LONGITUD) > 0:
            raise ErrorComando("La tolerancia tiene que ser mayor que cero.")
        return None

    def pintado(self):
        return self._tris is not None

    def mostrar(self, v, ctx):
        if ctx.ventana is None:
            return
        if not self._listo(v):
            self._tris = self._valores = None
            self._cursor.setText("Pasá el cursor por la pieza para ver su valor.")
            if self._panel is not None:
                self._panel.widgets["extremos"].setText(self._extremos(v, ctx))
            ctx.ventana.aplicar_analisis()
            return
        try:
            self.construir(v, ctx)
        except ErrorComando:
            return
        p = self.params(v, ctx)
        datos = analisis_vista.calcular(self.TIPO_ANALISIS, p, ctx.estado, ctx.doc.propiedades)
        analisis_vista.aplicar(ctx.ventana.visor, datos)
        cuerpo = p["cuerpos"][0]
        vertices, valores = datos["valores"][cuerpo]
        self._tris, self._valores = vertices.reshape(-1, 3, 3), valores
        self._escala.tolerancia = p["tolerancia"]
        self._escala.update()
        if self._panel is not None:
            self._panel.widgets["extremos"].setText(self._extremos(v, ctx))
        if self._sonda is None:
            self._sonda = _Sonda(ctx.ventana.visor, self)

    def sondear(self, visor, pos):
        """Valor bajo el cursor: en la caja del panel y en una etiqueta junto a la pieza."""
        if self._tris is None or self._cursor is None:
            return
        punto = None
        if pos is not None:
            o, d = visor.rayo(pos)
            t = rayo_triangulos(o, d, self._tris)
            i = int(np.argmin(t))
            if np.isfinite(t[i]):
                punto = o + d * float(t[i])
                k = i * 3 + int(np.argmin(np.linalg.norm(self._tris[i] - punto, axis=1)))
                texto = _mm(float(self._valores[k]))
        if punto is None:
            self._cursor.setText("Pasá el cursor por la pieza para ver su valor.")
            visor.set_capa(_CAPA, [])
            visor.set_etiquetas(_CAPA, [])
            return
        self._cursor.setText(f"Bajo el cursor: {texto}")
        visor.set_capa(_CAPA, [("puntos", np.array([punto]), (0.1, 0.1, 0.1), 7)])
        visor.set_etiquetas(_CAPA, [(punto, texto)])

    def al_cerrar(self, ctx):
        super().al_cerrar(ctx)
        self._tris = self._valores = None
        if ctx.ventana is not None:
            ctx.ventana.visor.set_capa(_CAPA, [])
            ctx.ventana.visor.set_etiquetas(_CAPA, [])
            if self._sonda is not None:
                ctx.ventana.visor.removeEventFilter(self._sonda)
                self._sonda.deleteLater()
                self._sonda = None


registrar(MapaDesviacion)
