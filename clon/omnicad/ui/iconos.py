# -*- coding: utf-8 -*-
"""
Íconos propios dibujados con QPainter (vectoriales, en una grilla de 32×32).

Imitan el ESTILO de la cinta de Fusion 360 (sólidos azules en isométrica, bocetos con trazo
punteado y un "+" verde, colores planos), pero están dibujados desde cero: no se copia ni se
extrae ningún ícono de la instalación de Autodesk (regla del proyecto: D:\\Autodesk solo lectura
y sin recursos propietarios). El estado deshabilitado lo genera Qt (versión gris).
"""
import math

from PySide6.QtCore import QPointF, QRectF, Qt
from PySide6.QtGui import QBrush, QColor, QFont, QIcon, QPainter, QPainterPath, QPen, QPixmap, QPolygonF, QRadialGradient

AZUL_ARRIBA, AZUL_FRENTE, AZUL_LADO, AZUL_BORDE = (QColor("#9fcff5"), QColor("#4a9be0"), QColor("#2b78c2"),
                                                  QColor("#1d5a94"))
GRIS_OSCURO, GRIS, VERDE, NARANJA, ROJO = (QColor("#4d4d4d"), QColor("#9a9a9a"), QColor("#2fa84f"),
                                           QColor("#ef9a2a"), QColor("#d64545"))
_cache = {}


def icono(nombre, tam=32):
    """QIcon del nombre pedido (cacheado). Nombre desconocido → ícono vacío (no rompe la UI)."""
    clave = (nombre, tam)
    if clave not in _cache:
        ico = QIcon()
        for escala in (1, 2):
            ico.addPixmap(pixmap(nombre, tam, escala))
        _cache[clave] = ico
    return _cache[clave]


def pixmap(nombre, tam=32, escala=2):
    pm = QPixmap(int(tam * escala), int(tam * escala))
    pm.setDevicePixelRatio(escala)
    pm.fill(Qt.transparent)
    funcion = DIBUJOS.get(nombre)
    if funcion:
        p = QPainter(pm)
        p.setRenderHint(QPainter.Antialiasing)
        p.scale(tam / 32, tam / 32)
        funcion(p)
        p.end()
    return pm


# ---------------------------------------------------------------- ayudantes
def _iso(x, y, z, cx=16.0, cy=16.0, k=1.0):
    return QPointF(cx + (x - y) * 0.866 * k, cy + (x + y) * 0.5 * k - z * k)


def _poli(p, puntos, relleno, borde=AZUL_BORDE, ancho=0.9):
    p.setPen(QPen(borde, ancho) if borde else Qt.NoPen)
    p.setBrush(QBrush(relleno) if relleno else Qt.NoBrush)
    p.drawPolygon(QPolygonF(puntos))


def _caja(p, a, b, h, cx, cy, k=1.0, colores=(AZUL_ARRIBA, AZUL_FRENTE, AZUL_LADO), borde=AZUL_BORDE):
    """Caja a×b×h en isométrica; (cx, cy) es la proyección del vértice (0, 0, 0)."""
    q = lambda x, y, z: _iso(x, y, z, cx, cy, k)  # noqa: E731
    arriba, frente, lado = colores
    _poli(p, [q(0, b, 0), q(a, b, 0), q(a, b, h), q(0, b, h)], frente, borde)
    _poli(p, [q(a, 0, 0), q(a, b, 0), q(a, b, h), q(a, 0, h)], lado, borde)
    _poli(p, [q(0, 0, h), q(a, 0, h), q(a, b, h), q(0, b, h)], arriba, borde)


def _flecha(p, x0, y0, x1, y1, color=GRIS_OSCURO, ancho=2.0, punta=4.5):
    p.setPen(QPen(color, ancho, Qt.SolidLine, Qt.RoundCap))
    p.drawLine(QPointF(x0, y0), QPointF(x1, y1))
    ang = math.atan2(y1 - y0, x1 - x0)
    p.setPen(Qt.NoPen)
    p.setBrush(color)
    pts = [QPointF(x1 + math.cos(ang) * 1.5, y1 + math.sin(ang) * 1.5),
           QPointF(x1 - math.cos(ang - 0.5) * punta, y1 - math.sin(ang - 0.5) * punta),
           QPointF(x1 - math.cos(ang + 0.5) * punta, y1 - math.sin(ang + 0.5) * punta)]
    p.drawPolygon(QPolygonF(pts))


def _mas(p, cx, cy, r=4.5, color=VERDE):
    p.setPen(QPen(color, 2.6, Qt.SolidLine, Qt.FlatCap))
    p.drawLine(QPointF(cx - r, cy), QPointF(cx + r, cy))
    p.drawLine(QPointF(cx, cy - r), QPointF(cx, cy + r))


def _punteado(p, rect, color=GRIS_OSCURO, ancho=1.3):
    pen = QPen(color, ancho)
    pen.setDashPattern([2.2, 1.8])
    p.setPen(pen)
    p.setBrush(Qt.NoBrush)
    p.drawRect(rect)


def _cilindro(p, cx, arriba, abajo, r, rv=None, colores=(AZUL_ARRIBA, AZUL_FRENTE)):
    rv = rv if rv is not None else r * 0.38
    cuerpo = QPainterPath()
    cuerpo.moveTo(cx - r, arriba)
    cuerpo.lineTo(cx - r, abajo)
    cuerpo.arcTo(QRectF(cx - r, abajo - rv, 2 * r, 2 * rv), 180, 180)
    cuerpo.lineTo(cx + r, arriba)
    p.setPen(QPen(AZUL_BORDE, 0.9))
    p.setBrush(colores[1])
    p.drawPath(cuerpo)
    p.setBrush(colores[0])
    p.drawEllipse(QRectF(cx - r, arriba - rv, 2 * r, 2 * rv))


# ---------------------------------------------------------------- dibujos (grilla 32×32)
def _boceto(p):
    _punteado(p, QRectF(5, 6, 19, 17))
    p.setPen(Qt.NoPen)
    p.setBrush(GRIS_OSCURO)
    for x, y in ((5, 6), (24, 6), (5, 23), (24, 23)):
        p.drawRect(QRectF(x - 1.6, y - 1.6, 3.2, 3.2))
    _mas(p, 25, 25)


def _boceto_bloqueado(p):
    """Boceto totalmente restringido en el navegador (Fusion le pone un candado al ícono)."""
    _punteado(p, QRectF(4, 5, 19, 17))
    p.setPen(Qt.NoPen)
    p.setBrush(GRIS_OSCURO)
    for x, y in ((4, 5), (23, 5), (4, 22), (23, 22)):
        p.drawRect(QRectF(x - 1.6, y - 1.6, 3.2, 3.2))
    p.save()
    p.translate(14, 13)
    p.scale(0.62, 0.62)
    _r_fijo(p)
    p.restore()


def _extruir(p):
    _caja(p, 9, 9, 8, 13, 15, 1.0)
    _flecha(p, 27, 24, 27, 4)


def _revolucion(p):
    banda = QPainterPath()
    banda.moveTo(4, 20)
    banda.cubicTo(6, 9, 26, 9, 28, 20)
    banda.lineTo(28, 25)
    banda.cubicTo(25, 15, 7, 15, 4, 25)
    banda.closeSubpath()
    p.setPen(QPen(AZUL_BORDE, 0.9))
    p.setBrush(AZUL_FRENTE)
    p.drawPath(banda)
    tapa = QPainterPath()
    tapa.moveTo(4, 20)
    tapa.cubicTo(6, 9, 26, 9, 28, 20)
    tapa.cubicTo(25, 12.5, 7, 12.5, 4, 20)
    p.setBrush(AZUL_ARRIBA)
    p.drawPath(tapa)


def _caja_ico(p):
    _caja(p, 12, 12, 12, 16, 16, 1.0)


def _cilindro_ico(p):
    _cilindro(p, 16, 9, 24, 9)


def _esfera(p):
    g = QRadialGradient(QPointF(12.5, 11.5), 14)
    g.setColorAt(0, AZUL_ARRIBA)
    g.setColorAt(0.55, AZUL_FRENTE)
    g.setColorAt(1, AZUL_LADO)
    p.setPen(QPen(AZUL_BORDE, 0.9))
    p.setBrush(QBrush(g))
    p.drawEllipse(QRectF(5, 5, 22, 22))


def _toroide(p):
    anillo = QPainterPath()
    anillo.addEllipse(QRectF(3, 8, 26, 17))
    anillo.addEllipse(QRectF(11, 13, 10, 6))
    anillo.setFillRule(Qt.OddEvenFill)
    g = QRadialGradient(QPointF(13, 12), 16)
    g.setColorAt(0, AZUL_ARRIBA)
    g.setColorAt(1, AZUL_LADO)
    p.setPen(QPen(AZUL_BORDE, 0.9))
    p.setBrush(QBrush(g))
    p.drawPath(anillo)


def _combinar(p):
    _caja(p, 8, 8, 8, 12, 10, 1.0)
    _caja(p, 8, 8, 8, 20, 17, 1.0)


def _parametros(p):
    f = QFont("Times New Roman", 17)
    f.setItalic(True)
    p.setFont(f)
    p.setPen(GRIS_OSCURO)
    p.drawText(QRectF(0, 0, 32, 30), Qt.AlignCenter, "fx")


def _calcular(p):
    p.setPen(QPen(VERDE, 2.6, Qt.SolidLine, Qt.RoundCap))
    p.setBrush(Qt.NoBrush)
    p.drawArc(QRectF(6, 6, 20, 20), 40 * 16, 270 * 16)
    _flecha(p, 23.5, 8.5, 25.5, 11.5, VERDE, 2.4, 5)


def _importar(p):
    _caja(p, 9, 9, 7, 13, 14, 1.0, (QColor("#f3d9a8"), QColor("#e9b45e"), QColor("#cf9236")), QColor("#9a6a22"))
    _flecha(p, 4, 4, 12, 13, AZUL_LADO, 2.4)


def _exportar(p):
    _caja(p, 9, 9, 7, 13, 14, 1.0)
    _flecha(p, 18, 13, 28, 3, NARANJA, 2.4)


def _seleccionar(p):
    _punteado(p, QRectF(4, 5, 20, 17), VERDE, 1.4)
    p.setPen(QPen(GRIS_OSCURO, 0.9))
    p.setBrush(QColor("#ffffff"))
    p.drawPolygon(QPolygonF([QPointF(18, 13), QPointF(18, 28), QPointF(21.5, 24.5), QPointF(24.5, 30),
                             QPointF(26.5, 29), QPointF(23.5, 23.5), QPointF(28, 23)]))


def _plano(p):
    _poli(p, [QPointF(4, 22), QPointF(13, 6), QPointF(15, 9), QPointF(7, 26)], QColor("#8bc34a"), QColor("#4d7a20"))
    _poli(p, [QPointF(15, 25), QPointF(24, 6), QPointF(28, 8), QPointF(19, 28)], QColor("#f0a25a"), QColor("#a35d1d"))


def _medir(p):
    p.setPen(QPen(QColor("#a06a10"), 0.9))
    p.setBrush(QColor("#f2b233"))
    p.drawRect(QRectF(3, 13, 26, 8))
    p.setPen(QPen(QColor("#6b4708"), 1))
    for i, x in enumerate(range(6, 28, 3)):
        p.drawLine(QPointF(x, 13), QPointF(x, 16 if i % 2 else 18))
    p.setPen(QPen(GRIS_OSCURO, 1.2))
    p.drawLine(QPointF(3, 8), QPointF(29, 8))
    p.drawLine(QPointF(3, 5.5), QPointF(3, 10.5))
    p.drawLine(QPointF(29, 5.5), QPointF(29, 10.5))


def _lienzo(p):
    p.setPen(QPen(AZUL_BORDE, 0.9))
    p.setBrush(QColor("#7cc0f2"))
    p.drawRect(QRectF(4, 6, 24, 20))
    p.setBrush(QColor("#2b78c2"))
    p.drawPolygon(QPolygonF([QPointF(4, 26), QPointF(12, 15), QPointF(17, 21), QPointF(21, 17), QPointF(28, 26)]))
    p.setBrush(QColor("#ffffff"))
    p.setPen(Qt.NoPen)
    p.drawEllipse(QRectF(20, 9, 4.5, 4.5))


def _ensamblar(p):
    gris = (QColor("#f0f0f0"), QColor("#c9c9c9"), QColor("#a3a3a3"))
    _caja(p, 6, 6, 6, 10, 8, 1.0, gris, GRIS_OSCURO)
    _caja(p, 6, 6, 6, 19, 17, 1.0, gris, GRIS_OSCURO)
    _flecha(p, 23, 6, 23, 13, GRIS_OSCURO, 1.4, 3.5)


def _configurar(p):
    p.setPen(QPen(GRIS, 1))
    p.setBrush(QColor("#ffffff"))
    p.drawRect(QRectF(4, 8, 20, 18))
    for y in (14, 20):
        p.drawLine(QPointF(4, y), QPointF(24, y))
    p.drawLine(QPointF(11, 8), QPointF(11, 26))
    p.setPen(Qt.NoPen)
    p.setBrush(QColor("#1a73e8"))
    p.drawEllipse(QRectF(17, 2, 12, 12))
    p.setPen(QPen(QColor("#ffffff"), 1.6))
    p.drawLine(QPointF(23, 11), QPointF(23, 5.5))
    p.drawLine(QPointF(20.5, 8), QPointF(23, 5.5))
    p.drawLine(QPointF(25.5, 8), QPointF(23, 5.5))


def _impresion3d(p):
    p.setPen(QPen(GRIS_OSCURO, 1.2))
    p.setBrush(QColor("#e9e9e9"))
    p.drawRect(QRectF(4, 4, 24, 5))
    p.setBrush(GRIS_OSCURO)
    p.drawPolygon(QPolygonF([QPointF(13, 9), QPointF(19, 9), QPointF(16, 14)]))
    _caja(p, 8, 8, 5, 12, 19, 0.9)


def _datos(p):
    p.setPen(Qt.NoPen)
    p.setBrush(GRIS_OSCURO)
    for i in range(3):
        for j in range(3):
            p.drawRect(QRectF(6 + i * 7.5, 6 + j * 7.5, 5, 5))


def _archivo(p):
    p.setPen(QPen(GRIS_OSCURO, 1.2))
    p.setBrush(QColor("#ffffff"))
    p.drawPolygon(QPolygonF([QPointF(8, 4), QPointF(19, 4), QPointF(25, 10), QPointF(25, 28), QPointF(8, 28)]))
    p.drawPolyline(QPolygonF([QPointF(19, 4), QPointF(19, 10), QPointF(25, 10)]))
    for y in (15, 19, 23):
        p.drawLine(QPointF(11, y), QPointF(22, y))


def _guardar(p):
    p.setPen(QPen(GRIS_OSCURO, 1.2))
    p.setBrush(QColor("#6f7a86"))
    p.drawRoundedRect(QRectF(5, 5, 22, 22), 2, 2)
    p.setBrush(QColor("#ffffff"))
    p.drawRect(QRectF(9, 5, 14, 8))
    p.setBrush(QColor("#d9dde2"))
    p.drawRect(QRectF(9, 17, 14, 10))


def _arco_flecha(p, invertir):
    p.save()
    if invertir:
        p.translate(32, 0)
        p.scale(-1, 1)
    p.setPen(QPen(GRIS_OSCURO, 2.4, Qt.SolidLine, Qt.RoundCap))
    p.setBrush(Qt.NoBrush)
    camino = QPainterPath(QPointF(9, 13))
    camino.cubicTo(14, 7, 27, 9, 25, 22)
    p.drawPath(camino)
    p.setPen(Qt.NoPen)
    p.setBrush(GRIS_OSCURO)
    p.drawPolygon(QPolygonF([QPointF(4, 9), QPointF(12, 8), QPointF(8, 17)]))
    p.restore()


def _ayuda(p):
    p.setPen(QPen(GRIS_OSCURO, 1.6))
    p.setBrush(Qt.NoBrush)
    p.drawEllipse(QRectF(5, 5, 22, 22))
    f = QFont("Segoe UI", 13)
    f.setBold(True)
    p.setFont(f)
    p.drawText(QRectF(5, 4, 22, 23), Qt.AlignCenter, "?")


def _engranaje(p, color=GRIS_OSCURO):
    p.setPen(Qt.NoPen)
    p.setBrush(color)
    c = QPointF(16, 16)
    pts = []
    for i in range(16):
        a = i * math.pi / 8
        r = 12 if i % 2 == 0 else 9
        pts.append(QPointF(c.x() + r * math.cos(a), c.y() + r * math.sin(a)))
    camino = QPainterPath()
    camino.addPolygon(QPolygonF(pts))
    camino.closeSubpath()
    camino.addEllipse(c, 4, 4)
    camino.setFillRule(Qt.OddEvenFill)
    p.drawPath(camino)


def _ojo(p, tachado=False):
    p.setPen(QPen(GRIS_OSCURO, 1.6))
    p.setBrush(Qt.NoBrush)
    camino = QPainterPath(QPointF(3, 16))
    camino.quadTo(16, 4, 29, 16)
    camino.quadTo(16, 28, 3, 16)
    p.drawPath(camino)
    p.setBrush(GRIS_OSCURO)
    p.drawEllipse(QPointF(16, 16), 4, 4)
    if tachado:
        p.setPen(QPen(GRIS_OSCURO, 1.8))
        p.drawLine(QPointF(5, 27), QPointF(27, 5))


def _componente(p):
    blanco = (QColor("#ffffff"), QColor("#f1f1f1"), QColor("#dcdcdc"))
    _caja(p, 12, 12, 12, 16, 16, 1.0, blanco, GRIS_OSCURO)


def _cuerpo(p):
    _caja(p, 12, 12, 11, 16, 16, 1.0, (QColor("#dfe7ef"), QColor("#a9b6c4"), QColor("#8494a6")), QColor("#4a5563"))


def _carpeta(p):
    p.setPen(QPen(GRIS_OSCURO, 1.2))
    p.setBrush(QColor("#ffffff"))
    p.drawPolygon(QPolygonF([QPointF(3, 9), QPointF(12, 9), QPointF(14, 12), QPointF(29, 12), QPointF(29, 26),
                             QPointF(3, 26)]))


def _unidades(p):
    _archivo(p)
    p.setPen(QPen(QColor("#a06a10"), 0.8))
    p.setBrush(QColor("#f2b233"))
    p.drawRect(QRectF(6, 22, 21, 6))


def _origen(p):
    for color, (x, y) in ((ROJO, (28, 22)), (VERDE, (24, 8)), (AZUL_LADO, (9, 3))):
        _flecha(p, 9, 22, x, y, color, 2, 4)


def _orbita(p):
    p.setPen(QPen(GRIS_OSCURO, 1.6))
    p.setBrush(Qt.NoBrush)
    p.drawEllipse(QRectF(4, 10, 24, 12))
    p.setPen(Qt.NoPen)
    p.setBrush(AZUL_FRENTE)
    p.drawEllipse(QPointF(16, 16), 4.5, 4.5)
    _flecha(p, 22, 21.6, 15, 22, GRIS_OSCURO, 1.6, 4)


def _encuadre(p):
    for x1, y1 in ((16, 3), (16, 29), (3, 16), (29, 16)):
        _flecha(p, 16, 16, x1, y1, GRIS_OSCURO, 1.8, 4.5)


def _lupa(p):
    p.setPen(QPen(GRIS_OSCURO, 2))
    p.setBrush(Qt.NoBrush)
    p.drawEllipse(QRectF(5, 7, 15, 15))
    p.setPen(QPen(GRIS_OSCURO, 3.2, Qt.SolidLine, Qt.RoundCap))
    p.drawLine(QPointF(18, 20), QPointF(25, 27))


def _zoom(p):
    _lupa(p)
    p.setPen(QPen(GRIS_OSCURO, 1.6))
    p.drawLine(QPointF(23, 5), QPointF(29, 5))
    p.drawLine(QPointF(26, 2), QPointF(26, 8))
    p.drawLine(QPointF(23, 11), QPointF(29, 11))


def _ajustar(p):
    _punteado(p, QRectF(3, 4, 22, 21), GRIS_OSCURO, 1.1)
    _lupa(p)


def _visualizacion(p):
    p.setPen(QPen(GRIS_OSCURO, 1.4))
    p.setBrush(QColor("#d9dde2"))
    p.drawRect(QRectF(4, 6, 24, 16))
    p.drawLine(QPointF(16, 22), QPointF(16, 26))
    p.drawLine(QPointF(10, 27), QPointF(22, 27))


def _rejilla(p):
    p.setPen(QPen(GRIS_OSCURO, 1.3))
    for i in range(4):
        p.drawLine(QPointF(5 + i * 7.3, 5), QPointF(5 + i * 7.3, 27))
        p.drawLine(QPointF(5, 5 + i * 7.3), QPointF(27, 5 + i * 7.3))


def _casa(p):
    p.setPen(QPen(GRIS_OSCURO, 1.4))
    p.setBrush(QColor("#ffffff"))
    p.drawPolygon(QPolygonF([QPointF(16, 5), QPointF(28, 16), QPointF(24, 16), QPointF(24, 27), QPointF(8, 27),
                             QPointF(8, 16), QPointF(4, 16)]))


def _captura(p):
    p.setPen(QPen(GRIS_OSCURO, 1.3))
    p.setBrush(QColor("#d9dde2"))
    p.drawRoundedRect(QRectF(4, 10, 24, 16), 2, 2)
    p.drawRect(QRectF(11, 7, 9, 3))
    p.setBrush(QColor("#ffffff"))
    p.drawEllipse(QPointF(16, 18), 5, 5)


def _tl(p, forma):
    """Botones de reproducción del timeline: inicio, anterior, reproducir, siguiente, fin."""
    p.setPen(Qt.NoPen)
    p.setBrush(GRIS_OSCURO)
    tri_der = lambda x: QPolygonF([QPointF(x, 9), QPointF(x + 11, 16), QPointF(x, 23)])  # noqa: E731
    tri_izq = lambda x: QPolygonF([QPointF(x + 11, 9), QPointF(x, 16), QPointF(x + 11, 23)])  # noqa: E731
    if forma == "inicio":
        p.drawRect(QRectF(8, 9, 2.4, 14))
        p.drawPolygon(tri_izq(11))
    elif forma == "fin":
        p.drawPolygon(tri_der(10))
        p.drawRect(QRectF(21.6, 9, 2.4, 14))
    elif forma == "anterior":
        p.drawPolygon(tri_izq(9))
        p.drawRect(QRectF(20.5, 13.5, 3, 5))
    elif forma == "siguiente":
        p.drawRect(QRectF(8.5, 13.5, 3, 5))
        p.drawPolygon(tri_der(12))
    else:
        p.drawPolygon(QPolygonF([QPointF(10, 7), QPointF(24, 16), QPointF(10, 25)]))


def _marcador(p):
    p.setPen(Qt.NoPen)
    p.setBrush(QColor("#222222"))
    p.drawPolygon(QPolygonF([QPointF(10, 2), QPointF(22, 2), QPointF(22, 6), QPointF(16, 11), QPointF(10, 6)]))
    p.drawRect(QRectF(15, 6, 2, 26))


# ---------------------------------------------------------------- bocetos y restricciones (grilla 32×32)
ROJO_REST = QColor("#d23c3c")  # rojo: Fijo, Punto medio y Polígono (como en la cinta de Fusion 2026)
GRIS_REST = QColor("#4a4a4a")  # el resto de las restricciones van en gris oscuro


def _trazo(p, color=GRIS_OSCURO, ancho=1.6):
    """Lápiz continuo de puntas y uniones redondeadas, sin relleno (geometría de boceto)."""
    p.setPen(QPen(color, ancho, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin))
    p.setBrush(Qt.NoBrush)


def _guion(p, color=GRIS_OSCURO, ancho=1.1):
    """Lápiz discontinuo para las líneas de construcción, sin relleno."""
    lapiz = QPen(color, ancho, Qt.SolidLine, Qt.FlatCap)
    lapiz.setDashPattern([2.6, 2.2])
    p.setPen(lapiz)
    p.setBrush(Qt.NoBrush)


def _linea(p, x0, y0, x1, y1):
    p.drawLine(QPointF(x0, y0), QPointF(x1, y1))


def _ptos(p, puntos, lado=3.2, color=GRIS_OSCURO):
    """Puntos de boceto: cuadraditos rellenos centrados en cada (x, y)."""
    p.setPen(Qt.NoPen)
    p.setBrush(color)
    for x, y in puntos:
        p.drawRect(QRectF(x - lado / 2, y - lado / 2, lado, lado))


def _en_circulo(cx, cy, r, ang):
    """Punto de una circunferencia; el ángulo (grados) se mide como en Qt: 0° a la derecha, antihorario."""
    a = math.radians(ang)
    return cx + r * math.cos(a), cy - r * math.sin(a)


def _arco_trazo(p, cx, cy, r, ang0, ang1):
    """Dibuja un arco de circunferencia con el lápiz actual (ángulos en grados, antihorarios)."""
    rect = QRectF(cx - r, cy - r, 2 * r, 2 * r)
    camino = QPainterPath()
    camino.arcMoveTo(rect, ang0)
    camino.arcTo(rect, ang0, ang1 - ang0)
    p.drawPath(camino)


def _arco_con_punta(p, cx, cy, r, ang0, ang1, color=GRIS_OSCURO, ancho=1.6, punta=4.0):
    """Arco con punta de flecha en el extremo final (ang1)."""
    sentido = 1 if ang1 > ang0 else -1
    p.setPen(QPen(color, ancho, Qt.SolidLine, Qt.RoundCap))
    p.setBrush(Qt.NoBrush)
    _arco_trazo(p, cx, cy, r, ang0, ang1 - sentido * 8)
    xa, ya = _en_circulo(cx, cy, r, ang1 - sentido * 8)
    xb, yb = _en_circulo(cx, cy, r, ang1)
    _flecha(p, xa, ya, xb, yb, color, ancho, punta)


def _regular(cx, cy, r, lados, giro=0.0):
    """Vértices de un polígono regular; `giro` es el ángulo (grados, horario en pantalla) del primer vértice."""
    puntos = []
    for k in range(lados):
        a = math.radians(giro + 360.0 * k / lados)
        puntos.append(QPointF(cx + r * math.cos(a), cy + r * math.sin(a)))
    return puntos


def _curva_por(puntos):
    """Curva suave (Catmull-Rom convertida a Bézier cúbicas) que pasa por todos los puntos dados."""
    camino = QPainterPath(QPointF(*puntos[0]))
    for i in range(len(puntos) - 1):
        x0, y0 = puntos[max(i - 1, 0)]
        x1, y1 = puntos[i]
        x2, y2 = puntos[i + 1]
        x3, y3 = puntos[min(i + 2, len(puntos) - 1)]
        camino.cubicTo(x1 + (x2 - x0) / 6, y1 + (y2 - y0) / 6, x2 - (x3 - x1) / 6, y2 - (y3 - y1) / 6, x2, y2)
    return camino


def _letras(p, rect, texto, color, px, negrita=True):
    """Texto corto centrado en `rect`, con tamaño en píxeles lógicos."""
    f = QFont("Segoe UI")
    f.setPixelSize(px)
    f.setBold(negrita)
    p.setFont(f)
    p.setPen(color)
    p.drawText(rect, Qt.AlignCenter, texto)


# ---- geometría de boceto (trazo fino gris oscuro, puntos cuadrados)
def _b_linea(p):
    _trazo(p)
    _linea(p, 6, 25, 26, 7)
    _ptos(p, [(6, 25), (26, 7)])


def _b_linea_punto_medio(p):
    _trazo(p)
    _linea(p, 5, 24, 27, 8)
    _ptos(p, [(5, 24), (27, 8)])
    p.setPen(QPen(GRIS_OSCURO, 1.4))  # el punto medio va hueco y algo mayor, para distinguirlo de los extremos
    p.setBrush(QColor("#ffffff"))
    p.drawRect(QRectF(13.6, 13.6, 4.8, 4.8))


def _b_rectangulo(p):
    _trazo(p)
    p.drawRect(QRectF(5, 9, 22, 14))
    _ptos(p, [(5, 9), (27, 9), (5, 23), (27, 23)])


def _b_rectangulo_3p(p):
    c, s = math.cos(math.radians(-20)), math.sin(math.radians(-20))  # inclinado 20° (antihorario)
    esq = [QPointF(16 + dx * c - dy * s, 16 + dx * s + dy * c) for dx, dy in ((-10, 6), (10, 6), (10, -6), (-10, -6))]
    _trazo(p)
    p.drawPolygon(QPolygonF(esq))
    _ptos(p, [(q.x(), q.y()) for q in esq[:3]])  # las tres esquinas que se marcan con el mouse


def _b_rectangulo_centro(p):
    _guion(p, GRIS_OSCURO, 1.0)  # diagonales de construcción
    _linea(p, 5, 8, 27, 24)
    _linea(p, 27, 8, 5, 24)
    _trazo(p)
    p.drawRect(QRectF(5, 8, 22, 16))
    _ptos(p, [(16, 16)])


def _b_circulo(p):
    _trazo(p)
    p.drawEllipse(QPointF(16, 16), 10.5, 10.5)
    _ptos(p, [(16, 16)])


def _b_circulo_2p(p):
    _trazo(p)
    p.drawEllipse(QPointF(16, 16), 10.5, 10.5)
    _guion(p, GRIS_OSCURO, 1.1)
    _linea(p, 5.5, 16, 26.5, 16)  # diámetro
    _ptos(p, [(5.5, 16), (26.5, 16)])


def _b_circulo_3p(p):
    _trazo(p)
    p.drawEllipse(QPointF(16, 16), 10.5, 10.5)
    _ptos(p, [_en_circulo(16, 16, 10.5, a) for a in (150, 30, 270)])


def _b_arco(p):
    _trazo(p)
    _arco_trazo(p, 16, 23, 12, 10, 170)
    _ptos(p, [_en_circulo(16, 23, 12, a) for a in (10, 90, 170)])  # extremos y punto intermedio


def _b_arco_centro(p):
    _guion(p, GRIS_OSCURO, 1.1)
    _linea(p, 9, 23, 24, 23)  # radio
    _trazo(p)
    _arco_trazo(p, 9, 23, 15, 0, 80)
    _ptos(p, [(9, 23), _en_circulo(9, 23, 15, 0), _en_circulo(9, 23, 15, 80)])


def _b_arco_tangente(p):
    _trazo(p)
    _linea(p, 5, 24, 15, 24)  # recta que continúa en un arco tangente
    _arco_trazo(p, 15, 13, 11, 270, 390)
    _ptos(p, [(5, 24), _en_circulo(15, 13, 11, 30)])


def _b_poligono(p):
    _trazo(p)
    p.drawPolygon(QPolygonF(_regular(16, 16, 11.5, 6)))


def _disco_guia(p, cx, cy, r):
    """Circunferencia de construcción: discontinua y azul, con un velo celeste para que se lea sobre el polígono."""
    lapiz = QPen(AZUL_FRENTE, 1.1, Qt.SolidLine, Qt.FlatCap)
    lapiz.setDashPattern([2.6, 2.2])
    p.setPen(lapiz)
    p.setBrush(QColor(159, 207, 245, 110))
    p.drawEllipse(QPointF(cx, cy), r, r)


def _b_poligono_inscrito(p):
    _disco_guia(p, 16, 16, 11.5)  # circunferencia que pasa por los vértices
    _trazo(p)
    p.drawPolygon(QPolygonF(_regular(16, 16, 11.5, 6)))


def _b_poligono_circunscrito(p):
    _disco_guia(p, 16, 16, 12 * 0.866)  # circunferencia tangente a los lados (apotema = R·cos 30°)
    _trazo(p)
    p.drawPolygon(QPolygonF(_regular(16, 16, 12, 6)))


def _b_poligono_arista(p):
    pts = _regular(16, 16, 11.5, 6)
    _trazo(p)
    p.drawPolygon(QPolygonF(pts))
    p.setPen(QPen(GRIS_OSCURO, 3.6, Qt.SolidLine, Qt.FlatCap))  # la arista que se define, resaltada
    p.drawLine(pts[1], pts[2])


def _b_punto(p):
    _trazo(p, GRIS_OSCURO, 1.2)
    _linea(p, 7, 16, 25, 16)
    _linea(p, 16, 7, 16, 25)
    _ptos(p, [(16, 16)], 4.4)


def _b_elipse(p):
    p.save()
    p.translate(16, 16)
    p.rotate(-20)
    _trazo(p)
    p.drawEllipse(QPointF(0, 0), 12.5, 7.5)
    p.restore()
    _ptos(p, [(16, 16)])


def _b_ranura(p):
    p.save()
    p.translate(16, 16)
    p.rotate(-25)
    _trazo(p)
    p.drawRoundedRect(QRectF(-12, -5.5, 24, 11), 5.5, 5.5)
    _guion(p, GRIS_OSCURO, 1.0)  # eje entre los centros de los extremos
    _linea(p, -6.5, 0, 6.5, 0)
    p.restore()
    dx, dy = 6.5 * math.cos(math.radians(25)), 6.5 * math.sin(math.radians(25))
    _ptos(p, [(16 - dx, 16 + dy), (16 + dx, 16 - dy)])  # los puntos no se giran: quedan alineados a la grilla


def _b_spline(p):
    pts = [(5, 22), (12, 10), (20, 22), (27, 10)]
    _trazo(p)
    p.drawPath(_curva_por(pts))
    _ptos(p, pts)


def _b_conica(p):
    camino = QPainterPath(QPointF(6, 9))
    camino.quadTo(QPointF(16, 34), QPointF(26, 9))  # parábola
    _trazo(p)
    p.drawPath(camino)
    _guion(p, GRIS_OSCURO, 1.0)
    _linea(p, 6, 9, 26, 9)
    _ptos(p, [(6, 9), (26, 9), (16, 21.5)])


def _b_texto(p):
    p.setPen(QPen(GRIS_OSCURO, 2.6, Qt.SolidLine, Qt.FlatCap, Qt.MiterJoin))
    p.setBrush(Qt.NoBrush)
    p.drawPolyline(QPolygonF([QPointF(7, 27), QPointF(16, 7), QPointF(25, 27)]))
    _linea(p, 10.1, 20.5, 21.9, 20.5)


def _b_simetria(p):
    _guion(p, GRIS_OSCURO, 1.2)  # eje de simetría
    _linea(p, 16, 3, 16, 29)
    _trazo(p)
    p.drawPolygon(QPolygonF([QPointF(12.5, 8), QPointF(12.5, 25), QPointF(4, 25)]))
    p.drawPolygon(QPolygonF([QPointF(19.5, 8), QPointF(19.5, 25), QPointF(28, 25)]))


def _b_patron_circular(p):
    for i in range(6):
        a = math.radians(-90 + 60 * i)
        p.setPen(QPen(GRIS_OSCURO, 1.4))
        p.setBrush(QBrush(AZUL_ARRIBA) if i == 0 else Qt.NoBrush)  # el primero es la pieza original
        p.drawEllipse(QPointF(16 + 9.5 * math.cos(a), 16 + 9.5 * math.sin(a)), 3.2, 3.2)


def _b_patron_rectangular(p):
    for i in range(3):
        for j in range(3):
            p.setPen(QPen(GRIS_OSCURO, 1.3))
            p.setBrush(QBrush(AZUL_ARRIBA) if i == 0 and j == 0 else Qt.NoBrush)
            p.drawRect(QRectF(5.5 + i * 8, 5.5 + j * 8, 5, 5))


def _b_proyectar(p):
    _poli(p, [QPointF(5, 23), QPointF(16, 17.5), QPointF(27, 23), QPointF(16, 28.5)], QColor("#cfe3f5"), AZUL_BORDE,
          1.0)
    _caja(p, 5, 5, 5, 16, 8.5, 1.0)
    _flecha(p, 16, 14, 16, 20.5, GRIS_OSCURO, 1.6, 4)


def _b_cota(p):
    _trazo(p, GRIS_OSCURO, 1.2)
    _linea(p, 5, 8, 5, 26)  # líneas de extensión
    _linea(p, 27, 8, 27, 26)
    _flecha(p, 16, 22, 6.5, 22, GRIS_OSCURO, 1.2, 3.6)  # línea de cota con doble flecha
    _flecha(p, 16, 22, 25.5, 22, GRIS_OSCURO, 1.2, 3.6)
    _letras(p, QRectF(5, 6, 22, 14), "10", GRIS_OSCURO, 10)


def _b_helice(p):
    n = 90
    pts = []
    for i in range(n + 1):
        t = i / n
        ang = t * 2.6 * 2 * math.pi
        r = 1.6 + 10 * t
        pts.append(QPointF(16 + r * math.cos(ang), 16 + r * math.sin(ang)))
    _trazo(p)
    p.drawPolyline(QPolygonF(pts))
    _ptos(p, [(pts[0].x(), pts[0].y()), (pts[-1].x(), pts[-1].y())])


def _b_empalme(p):
    _guion(p, GRIS_OSCURO, 1.0)  # la esquina viva original
    p.drawPolyline(QPolygonF([QPointF(6, 18), QPointF(6, 26), QPointF(14, 26)]))
    camino = QPainterPath(QPointF(6, 6))
    camino.lineTo(6, 18)
    camino.arcTo(QRectF(6, 10, 16, 16), 180, 90)
    camino.lineTo(26, 26)
    _trazo(p)
    p.drawPath(camino)
    _ptos(p, [(6, 6), (26, 26)])


def _b_chaflan(p):
    _guion(p, GRIS_OSCURO, 1.0)  # la esquina viva original
    p.drawPolyline(QPolygonF([QPointF(6, 17), QPointF(6, 26), QPointF(15, 26)]))
    _trazo(p)
    p.drawPolyline(QPolygonF([QPointF(6, 6), QPointF(6, 17), QPointF(15, 26), QPointF(26, 26)]))
    _ptos(p, [(6, 6), (26, 26)])


def _b_curva_fusion(p):
    camino = QPainterPath(QPointF(4.5, 23))
    camino.lineTo(9.5, 23)
    camino.cubicTo(16, 23, 16, 9, 22.5, 9)  # curva en S que une las dos rectas
    camino.lineTo(27.5, 9)
    _trazo(p)
    p.drawPath(camino)
    _ptos(p, [(4.5, 23), (27.5, 9)])
    _ptos(p, [(9.5, 23), (22.5, 9)], 2.4)


def _b_desfase(p):
    _trazo(p)
    _arco_trazo(p, 16, 30, 20, 50, 130)
    _arco_trazo(p, 16, 30, 12, 50, 130)
    _flecha(p, 16, 11.5, 16, 15.5, GRIS_OSCURO, 1.2, 3.2)  # sentido del desfase


def _b_recortar(p):
    _trazo(p, GRIS_OSCURO, 2.2)  # las dos hojas, que se cruzan en el pivote
    _linea(p, 12, 21.5, 23, 4)
    _linea(p, 20, 21.5, 9, 4)
    p.setPen(QPen(GRIS_OSCURO, 1.8))
    p.setBrush(QColor("#ffffff"))
    p.drawEllipse(QPointF(10, 25), 3.6, 3.6)  # anillos
    p.drawEllipse(QPointF(22, 25), 3.6, 3.6)
    p.drawEllipse(QPointF(16, 15.1), 1.7, 1.7)  # pivote


def _b_alargar(p):
    _trazo(p)
    _linea(p, 4, 16, 15, 16)
    _flecha(p, 15, 16, 22.5, 16, AZUL_FRENTE, 1.8, 4.5)
    _trazo(p, GRIS_OSCURO, 2.4)  # la barrera hasta donde se alarga
    _linea(p, 26.5, 5, 26.5, 27)
    _ptos(p, [(4, 16)])


def _b_partir(p):
    _trazo(p)
    _linea(p, 4, 24, 12.67, 18.22)  # recta partida en dos, con hueco al centro
    _linea(p, 19.33, 13.78, 28, 8)
    _trazo(p, GRIS_OSCURO, 1.6)
    _linea(p, 11.0, 15.7, 14.3, 20.7)  # marcas de corte
    _linea(p, 17.7, 11.3, 21.0, 16.3)
    _ptos(p, [(4, 24), (28, 8)])


def _b_escala(p):
    _trazo(p, GRIS_OSCURO, 1.5)
    p.drawRect(QRectF(5, 9, 18, 18))  # cuadrado grande
    p.setBrush(AZUL_ARRIBA)
    p.drawRect(QRectF(5, 19, 8, 8))  # cuadrado chico, el tamaño original
    _flecha(p, 13, 19, 26.5, 5.5, GRIS_OSCURO, 1.8, 4.5)


def _b_mover(p):
    for x1, y1 in ((16, 5), (16, 27), (5, 16), (27, 16)):
        _flecha(p, 16, 16, x1, y1, GRIS_OSCURO, 2.0, 5)
    _caja(p, 4, 4, 4, 16, 16, 1.0)  # el objeto que se desplaza


# ---- restricciones (glifos rojos)
def _r_horizontal_vertical(p):
    _trazo(p, GRIS_REST, 3.0)
    _linea(p, 6, 7, 26, 7)
    _linea(p, 16, 13, 16, 25)


def _r_coincidente(p):
    _trazo(p, GRIS_REST, 2.4)
    p.drawPolyline(QPolygonF([QPointF(4, 23), QPointF(16, 13), QPointF(28, 23)]))
    p.setPen(Qt.NoPen)
    p.setBrush(GRIS_REST)
    p.drawEllipse(QPointF(16, 13), 3.8, 3.8)


def _r_tangente(p):
    _trazo(p, GRIS_REST, 2.4)
    p.drawEllipse(QPointF(16, 15.5), 9, 9)
    _linea(p, 4, 24.5, 28, 24.5)


def _r_igual(p):
    _trazo(p, GRIS_REST, 3.0)
    _linea(p, 7, 12, 25, 12)
    _linea(p, 7, 20, 25, 20)


def _r_paralela(p):
    _trazo(p, GRIS_REST, 3.0)
    _linea(p, 9, 26, 17, 6)
    _linea(p, 17, 26, 25, 6)


def _r_perpendicular(p):
    _trazo(p, GRIS_REST, 3.0)
    _linea(p, 5, 25, 27, 25)
    _linea(p, 16, 25, 16, 6)


def _r_fijo(p):
    p.setPen(QPen(ROJO_REST, 2.6, Qt.SolidLine, Qt.FlatCap))
    p.setBrush(Qt.NoBrush)
    arco = QPainterPath(QPointF(11.5, 15))
    arco.lineTo(11.5, 11)
    arco.arcTo(QRectF(11.5, 6.5, 9, 9), 180, -180)  # asa del candado
    arco.lineTo(20.5, 15)
    p.drawPath(arco)
    p.setPen(Qt.NoPen)
    p.setBrush(ROJO_REST)
    p.drawRoundedRect(QRectF(8, 14, 16, 13), 2.2, 2.2)
    p.setBrush(QColor("#ffffff"))
    p.drawEllipse(QPointF(16, 19.5), 1.9, 1.9)  # ojo de la cerradura
    p.setPen(QPen(QColor("#ffffff"), 1.8, Qt.SolidLine, Qt.FlatCap))
    _linea(p, 16, 19.5, 16, 23.5)


def _r_punto_medio(p):
    _trazo(p, ROJO_REST, 2.6)
    p.drawPolygon(QPolygonF([QPointF(16, 5.5), QPointF(27, 25.5), QPointF(5, 25.5)]))


def _r_concentrica(p):
    _trazo(p, GRIS_REST, 2.4)
    p.drawEllipse(QPointF(16, 16), 11, 11)
    p.drawEllipse(QPointF(16, 16), 5.5, 5.5)


def _r_colineal(p):
    _guion(p, GRIS_REST, 1.4)  # la recta común, por detrás
    _linea(p, 3, 24, 29, 8.5)
    _trazo(p, GRIS_REST, 3.0)
    _linea(p, 4, 23.4, 11.7, 18.8)
    _linea(p, 20.3, 13.6, 28, 9)


def _r_simetria(p):
    _guion(p, GRIS_REST, 1.4)  # eje de simetría
    _linea(p, 16, 3, 16, 29)
    _trazo(p, GRIS_REST, 2.6)
    p.drawPolyline(QPolygonF([QPointF(13.5, 6), QPointF(8, 6), QPointF(8, 26), QPointF(13.5, 26)]))
    p.drawPolyline(QPolygonF([QPointF(18.5, 6), QPointF(24, 6), QPointF(24, 26), QPointF(18.5, 26)]))


def _r_curvatura(p):
    camino = QPainterPath(QPointF(4.5, 25))
    camino.lineTo(13, 25)
    camino.cubicTo(21, 25, 27, 20, 27, 10)  # la curva sale tangente a la recta
    _trazo(p, GRIS_REST, 2.6)
    p.drawPath(camino)
    _letras(p, QRectF(3, 3, 14, 15), "C", GRIS_REST, 14)


def _r_poligono(p):
    _trazo(p, ROJO_REST, 2.6)
    p.drawPolygon(QPolygonF(_regular(16, 17, 11.5, 5, -90)))


# ---- otros
def _terminar(p):
    p.setPen(Qt.NoPen)
    p.setBrush(VERDE)
    p.drawEllipse(QPointF(16, 16), 13, 13)
    p.setPen(QPen(QColor("#ffffff"), 3.4, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin))
    p.setBrush(Qt.NoBrush)
    p.drawPolyline(QPolygonF([QPointF(9.5, 16.5), QPointF(14, 21), QPointF(22.5, 11.5)]))


def _mirar_a(p):
    p.setPen(QPen(GRIS_OSCURO, 1.4))
    p.setBrush(QColor("#d9dde2"))
    p.drawRoundedRect(QRectF(9, 3, 20, 18), 1.5, 1.5)  # pantalla / plano
    p.setPen(QPen(AZUL_BORDE, 1))
    p.setBrush(AZUL_FRENTE)
    p.drawRect(QRectF(14.5, 7.5, 9, 9))  # la cara que se mira de frente
    _flecha(p, 4, 28, 13, 18, GRIS_OSCURO, 2.0, 4.5)


def _orbita_libre(p):
    p.setPen(QPen(GRIS_OSCURO, 1.6))
    p.setBrush(Qt.NoBrush)
    p.drawEllipse(QRectF(4, 13.5, 24, 12))
    p.setPen(Qt.NoPen)
    p.setBrush(AZUL_FRENTE)
    p.drawEllipse(QPointF(16, 19.5), 4.5, 4.5)
    _flecha(p, 22, 24.7, 15, 25.5, GRIS_OSCURO, 1.6, 4)
    _arco_con_punta(p, 16, 18.5, 13, 20, 160, GRIS_OSCURO, 1.6, 4)  # giro libre en cualquier dirección
    _arco_con_punta(p, 16, 18.5, 13, 160, 20, GRIS_OSCURO, 1.6, 4)


def _orbita_restringida(p):
    _trazo(p, GRIS_OSCURO, 1.4)
    _linea(p, 16, 3, 16, 29)  # eje vertical al que queda restringido el giro
    p.setPen(QPen(GRIS_OSCURO, 1.6))
    p.drawEllipse(QRectF(3, 11, 26, 10))
    p.setPen(Qt.NoPen)
    p.setBrush(AZUL_FRENTE)
    p.drawEllipse(QPointF(16, 16), 4.5, 4.5)
    _flecha(p, 23, 20.2, 16, 21, GRIS_OSCURO, 1.6, 4)


def _ventana_zoom(p):
    _punteado(p, QRectF(3, 4, 21, 18), GRIS_OSCURO, 1.2)
    p.setPen(QPen(GRIS_OSCURO, 1.8))
    p.setBrush(QColor("#ffffff"))
    p.drawEllipse(QPointF(20.5, 18.5), 5.5, 5.5)
    p.setPen(QPen(GRIS_OSCURO, 3.0, Qt.SolidLine, Qt.RoundCap))
    _linea(p, 24.6, 22.6, 28.5, 26.5)


def _vistas_multiples(p):
    p.setPen(QPen(GRIS_OSCURO, 1.4))
    for i in range(2):
        for j in range(2):
            p.setBrush(AZUL_ARRIBA if i == 0 and j == 0 else QColor("#d9dde2"))
            p.drawRect(QRectF(4 + i * 13, 4.5 + j * 13, 11, 10))


def _pantalla_completa(p):
    for sx, sy in ((-1, -1), (1, -1), (1, 1), (-1, 1)):
        cx, cy = 16 + sx * 12, 16 + sy * 12
        _trazo(p, GRIS_OSCURO, 2.2)
        p.drawPolyline(QPolygonF([QPointF(cx - sx * 8, cy), QPointF(cx, cy), QPointF(cx, cy - sy * 8)]))
        _flecha(p, cx - sx * 9, cy - sy * 9, cx - sx * 4, cy - sy * 4, GRIS_OSCURO, 1.6, 3.6)


def _plano_desfase(p):
    _poli(p, [QPointF(4, 28), QPointF(12, 20), QPointF(27, 20), QPointF(19, 28)], QColor(240, 162, 90, 215),
          QColor("#a35d1d"))
    _poli(p, [QPointF(5, 12), QPointF(13, 4), QPointF(28, 4), QPointF(20, 12)], QColor(248, 217, 184, 190),
          QColor("#c98a4d"))
    _flecha(p, 17, 12.8, 17, 19, GRIS_OSCURO, 1.4, 3.5)  # separación entre los dos planos


DIBUJOS = {
    "boceto": _boceto, "boceto_bloqueado": _boceto_bloqueado, "extruir": _extruir, "revolucion": _revolucion, "caja": _caja_ico,
    "cilindro": _cilindro_ico, "esfera": _esfera, "toroide": _toroide, "combinar": _combinar,
    "parametros": _parametros, "calcular": _calcular, "importar": _importar, "exportar": _exportar,
    "seleccionar": _seleccionar, "plano": _plano, "medir": _medir, "lienzo": _lienzo, "ensamblar": _ensamblar,
    "configurar": _configurar, "impresion3d": _impresion3d, "datos": _datos, "archivo": _archivo,
    "guardar": _guardar, "deshacer": lambda p: _arco_flecha(p, False), "rehacer": lambda p: _arco_flecha(p, True),
    "ayuda": _ayuda, "engranaje": _engranaje, "ojo": _ojo, "ojo_no": lambda p: _ojo(p, True),
    "componente": _componente, "cuerpo": _cuerpo, "carpeta": _carpeta, "unidades": _unidades,
    "origen": _origen, "orbita": _orbita, "encuadre": _encuadre, "zoom": _zoom, "ajustar": _ajustar, "buscar": _lupa,
    "visualizacion": _visualizacion, "rejilla": _rejilla, "casa": _casa, "captura": _captura,
    "tl_inicio": lambda p: _tl(p, "inicio"), "tl_anterior": lambda p: _tl(p, "anterior"),
    "tl_reproducir": lambda p: _tl(p, "reproducir"), "tl_siguiente": lambda p: _tl(p, "siguiente"),
    "tl_fin": lambda p: _tl(p, "fin"), "marcador": _marcador,
    # geometría de boceto
    "linea": _b_linea, "linea_punto_medio": _b_linea_punto_medio, "rectangulo": _b_rectangulo,
    "rectangulo_3p": _b_rectangulo_3p, "rectangulo_centro": _b_rectangulo_centro, "circulo": _b_circulo,
    "circulo_2p": _b_circulo_2p, "circulo_3p": _b_circulo_3p, "arco": _b_arco, "arco_centro": _b_arco_centro,
    "arco_tangente": _b_arco_tangente, "poligono": _b_poligono, "poligono_inscrito": _b_poligono_inscrito,
    "poligono_circunscrito": _b_poligono_circunscrito, "poligono_arista": _b_poligono_arista, "punto": _b_punto,
    "elipse": _b_elipse, "ranura": _b_ranura, "spline": _b_spline, "conica": _b_conica, "texto": _b_texto,
    "simetria_boceto": _b_simetria, "patron_circular": _b_patron_circular,
    "patron_rectangular": _b_patron_rectangular, "proyectar": _b_proyectar, "cota": _b_cota, "helice": _b_helice,
    "empalme": _b_empalme, "chaflan_boceto": _b_chaflan, "curva_fusion": _b_curva_fusion, "desfase": _b_desfase,
    "recortar": _b_recortar, "alargar": _b_alargar, "partir": _b_partir, "escala_boceto": _b_escala,
    "mover": _b_mover,
    # restricciones
    "r_horizontal_vertical": _r_horizontal_vertical, "r_coincidente": _r_coincidente, "r_tangente": _r_tangente,
    "r_igual": _r_igual, "r_paralela": _r_paralela, "r_perpendicular": _r_perpendicular, "r_fijo": _r_fijo,
    "r_punto_medio": _r_punto_medio, "r_concentrica": _r_concentrica, "r_colineal": _r_colineal,
    "r_simetria": _r_simetria, "r_curvatura": _r_curvatura, "r_poligono": _r_poligono,
    # otros
    "terminar": _terminar, "mirar_a": _mirar_a, "orbita_libre": _orbita_libre,
    "orbita_restringida": _orbita_restringida, "ventana_zoom": _ventana_zoom,
    "vistas_multiples": _vistas_multiples, "pantalla_completa": _pantalla_completa,
    "plano_desfase": _plano_desfase,
}


# Íconos de los comandos 3D, superficie, malla, chapa, etc. (dibujados en iconos_extra.py).
from .iconos_extra import DIBUJOS_EXTRA  # noqa: E402

DIBUJOS.update(DIBUJOS_EXTRA)
