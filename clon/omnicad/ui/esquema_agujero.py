# -*- coding: utf-8 -*-
"""FU-2: el corte del agujero con sus cotas editables dentro del diálogo, como el de Fusion (ayuda «Create a hole in a
solid body»: «Use the dimension and settings preview in the Hole dialog to fine tune your settings»).

Es un dibujo fijo por tipo (simple, escariado, avellanado) y punta (plana o en ángulo), no a escala. Las cajas son los
mismos campos `Expresion` del panel marcados `en_esquema`: este widget los adopta y los pone sobre su cota, así que
siguen con su valor, su fx, su rojo y su visibilidad según el tipo."""
from PySide6.QtCore import QPointF, QRectF, Qt
from PySide6.QtGui import QColor, QPainter, QPainterPath, QPen, QPolygonF
from PySide6.QtWidgets import QWidget

CLAVES = ("diametro", "profundidad", "angulo_punta", "diam_abocardado", "prof_abocardado", "diam_avellanado",
          "angulo_avellanado")
ALTO, ANCHO_CAJA, ALTO_CAJA = 214, 96, 24
FONDO, PIEZA, LINEA = QColor("#f4f5f7"), QColor("#b9bec6"), QColor("#2b2f36")


class EsquemaAgujero(QWidget):
    def __init__(self, panel):
        super().__init__()
        self.panel = panel
        self.setObjectName("esquema_agujero")
        self.setFixedHeight(ALTO)
        for clave in CLAVES:                      # las cajas del panel pasan al dibujo
            caja = panel.widgets[clave]
            caja.setParent(self)
            caja.setFixedSize(ANCHO_CAJA, ALTO_CAJA)

    def _forma(self):
        """Medidas del dibujo en píxeles: centro, bocas y alturas según el tipo y la punta."""
        v = self.panel.valores
        tipo, punta = v.get("tipo", "simple"), v.get("punta", "angulo")
        cx, arriba, fondo, b = self.width() / 2 - 6, 44.0, 150.0, 22.0
        boca = {"abocardado": 40.0, "avellanado": 44.0}.get(tipo, b)
        baja = {"abocardado": 28.0, "avellanado": 22.0}.get(tipo, 0.0)
        return tipo, punta == "angulo", cx, arriba, fondo, b, boca, baja

    def _cajas(self):
        """clave → esquina de su caja, junto a la cota que le corresponde."""
        tipo, en_punta, cx, arriba, fondo, b, boca, baja = self._forma()
        w = ANCHO_CAJA
        pos = {"profundidad": (cx + b + 34, (arriba + fondo) / 2 - ALTO_CAJA / 2),
               "angulo_punta": (cx + 30, fondo + 26)}
        if tipo == "simple":
            pos["diametro"] = (cx - w / 2, 6)
        else:
            pos["diametro"] = (cx - b - 18 - w, arriba + baja + 34)
            externo = "diam_abocardado" if tipo == "abocardado" else "diam_avellanado"
            pos[externo] = (cx - w / 2, 6)
            interno = "prof_abocardado" if tipo == "abocardado" else "angulo_avellanado"
            pos[interno] = (cx - boca - 18 - w, arriba + baja / 2 - ALTO_CAJA / 2)
        return {k: (min(max(4.0, x), self.width() - w - 4.0), y) for k, (x, y) in pos.items()}   # dentro del dibujo

    def paintEvent(self, _evento):
        for clave, (x, y) in self._cajas().items():
            self.panel.widgets[clave].move(int(x), int(y))
        tipo, en_punta, cx, arriba, fondo, b, boca, baja = self._forma()
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        p.setPen(Qt.NoPen)
        p.setBrush(FONDO)
        p.drawRoundedRect(QRectF(self.rect()).adjusted(0.5, 0.5, -0.5, -0.5), 6, 6)
        pieza = QRectF(cx - 92, arriba, 184, ALTO - arriba - 8)
        hueco = QPolygonF([QPointF(cx - boca, arriba)])
        if tipo == "abocardado":
            hueco += [QPointF(cx - boca, arriba + baja), QPointF(cx - b, arriba + baja)]
        elif tipo == "avellanado":
            hueco += [QPointF(cx - b, arriba + baja)]
        hueco += [QPointF(cx - b, fondo)]
        hueco += [QPointF(cx, fondo + 22)] if en_punta else []
        hueco += [QPointF(cx + b, fondo)]
        if tipo == "abocardado":
            hueco += [QPointF(cx + b, arriba + baja), QPointF(cx + boca, arriba + baja)]
        elif tipo == "avellanado":
            hueco += [QPointF(cx + b, arriba + baja)]
        hueco += [QPointF(cx + boca, arriba)]
        cuerpo = QPainterPath()
        cuerpo.addRect(pieza)
        corte = QPainterPath()
        corte.addPolygon(hueco)
        p.setBrush(PIEZA)
        p.drawPath(cuerpo.subtracted(corte))
        p.setPen(QPen(LINEA, 1.2))
        p.setBrush(Qt.NoBrush)
        p.drawPolygon(hueco)
        p.setPen(QPen(LINEA, 1.0, Qt.DashLine))
        p.drawLine(QPointF(cx, arriba - 6), QPointF(cx, fondo + 30))           # eje del agujero
        p.setPen(QPen(LINEA, 1.0))
        cotas = {"profundidad": (QPointF(cx + b + 24, arriba), QPointF(cx + b + 24, fondo))}
        if tipo == "simple":
            cotas["diametro"] = (QPointF(cx - b, arriba - 8), QPointF(cx + b, arriba - 8))
        else:
            cotas["diametro"] = (QPointF(cx - b, arriba + baja + 46), QPointF(cx + b, arriba + baja + 46))
            externo = "diam_abocardado" if tipo == "abocardado" else "diam_avellanado"
            cotas[externo] = (QPointF(cx - boca, arriba - 8), QPointF(cx + boca, arriba - 8))
            if tipo == "abocardado":
                cotas["prof_abocardado"] = (QPointF(cx - boca - 10, arriba), QPointF(cx - boca - 10, arriba + baja))
        for clave, (a, z) in cotas.items():
            if self.panel.widgets[clave].isVisibleTo(self):
                _cota(p, a, z)
        p.end()


def _cota(p, a, z):
    """Línea de cota con flechas en las dos puntas."""
    p.drawLine(a, z)
    d = z - a
    largo = (d.x() ** 2 + d.y() ** 2) ** 0.5 or 1.0
    u = QPointF(d.x() / largo, d.y() / largo)
    n = QPointF(-u.y(), u.x())
    for punta, hacia in ((a, u), (z, -u)):
        p.drawLine(punta, punta + hacia * 6 + n * 3)
        p.drawLine(punta, punta + hacia * 6 - n * 3)
