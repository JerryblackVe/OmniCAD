# -*- coding: utf-8 -*-
"""
Íconos adicionales (≈140) para los comandos de las pestañas de Fusion que no tenían dibujo propio:
sólido, modificar, construir, inspeccionar, insertar, ensamblar, seleccionar, superficie, malla,
chapa y espacios de trabajo.

Misma grilla 32×32 y mismo estilo que `iconos.py` (de donde se reusan los ayudantes); dibujados desde
cero, sin copiar nada de Autodesk. Convenciones de color:
  - azul en 3 tonos   → lo que crea o modifica el comando;  azul pálido → copias / estado anterior;
  - gris azulado      → el cuerpo existente sobre el que actúa;  blanco/gris → componentes;
  - naranja translúcido → planos de construcción; ejes en naranja oscuro punto y raya; puntos amarillos;
  - naranja/beige     → superficies (láminas finas);  verde azulado → mallas (triángulos visibles);
  - violeta           → formas (T-Splines).
`iconos.py` hace `DIBUJOS.update(DIBUJOS_EXTRA)` al final.
"""
import math

from PySide6.QtCore import QPointF, QRectF, Qt
from PySide6.QtGui import (QBrush, QColor, QLinearGradient, QPainterPath, QPen, QPolygonF, QRadialGradient,
                           QTransform)

# ---------------------------------------------------------------- paleta propia
GRISES, BORDE_GRIS = (QColor("#dfe7ef"), QColor("#a9b6c4"), QColor("#8494a6")), QColor("#4a5563")
OSCUROS = (QColor("#7d8a99"), QColor("#9aa7b6"), QColor("#6b7888"))            # interior de huecos grises
BLANCOS = (QColor("#ffffff"), QColor("#eeeeee"), QColor("#d4d4d4"))
GRIS_COMP = (QColor("#e6e6e6"), QColor("#c4c4c4"), QColor("#a2a2a2"))
FANTASMA, BORDE_FANTASMA = (QColor("#e2effb"), QColor("#c6def5"), QColor("#acccec")), QColor("#7fa9cf")
SUP, BORDE_SUP = (QColor("#fbe3c0"), QColor("#f2bd78"), QColor("#dc9a4c")), QColor("#9a6a22")
MALLA, BORDE_MALLA = (QColor("#cfe8e4"), QColor("#9ccbc5"), QColor("#76aba5")), QColor("#2e5c57")
METAL, BORDE_METAL = (QColor("#f4f4f4"), QColor("#c9c9c9"), QColor("#a4a4a4")), QColor("#5a5a5a")
VIOLETA = QColor("#553a91")
PLANO, PLANO_2, BORDE_PLANO = QColor(240, 162, 90, 200), QColor(250, 205, 150, 200), QColor("#a35d1d")
GRIS_PLANO, BORDE_GRIS_PLANO = QColor(205, 212, 220, 220), QColor("#6b7785")
EJE, PUNTO, BORDE_PUNTO = QColor("#b4531a"), QColor("#ffc233"), QColor("#6e4206")
AZUL_SEL = QColor("#d2ebff")                                                    # cara seleccionada
ROJOS = (QColor("#f59a92"), QColor("#d9453a"), QColor("#a72c22"))


# ---------------------------------------------------------------- ayudantes propios
def _azules():
    return AZUL_ARRIBA, AZUL_FRENTE, AZUL_LADO


def _q(ox, oy):
    """Proyector isométrico con el origen (0, 0, 0) en el punto (ox, oy) de la pantalla."""
    return lambda x, y, z: _iso(x, y, z, ox, oy)


def _centro(a, b, h):
    """Origen que deja centrada en el ícono una caja a×b×h."""
    return 16 - 0.433 * (a - b), 16 - (0.5 * (a + b) - h) / 2


def _caja_en(p, q, x, y, z, a, b, h, colores=None, borde=None):
    """Caja a×b×h con su vértice (0, 0, 0) en el punto (x, y, z) del proyector `q`."""
    o = q(x, y, z)
    _caja(p, a, b, h, o.x(), o.y(), 1.0, colores or _azules(), borde or AZUL_BORDE)


def _caja_c(p, a, b, h, colores=None, borde=None):
    """Caja centrada; devuelve su proyector."""
    q = _q(*_centro(a, b, h))
    _caja_en(p, q, 0, 0, 0, a, b, h, colores, borde)
    return q


def _cuadro(q, x0, y0, x1, y1, z):
    """Rectángulo horizontal (a la altura z) en isométrica."""
    return [q(x0, y0, z), q(x1, y0, z), q(x1, y1, z), q(x0, y1, z)]


def _hexagono(q, a, b, h):
    """Contorno (silueta) de una caja en isométrica."""
    return [q(0, 0, h), q(a, 0, h), q(a, 0, 0), q(a, b, 0), q(0, b, 0), q(0, b, h)]


def _camino(puntos):
    c = QPainterPath()
    c.addPolygon(QPolygonF(puntos))
    c.closeSubpath()
    return c


def _hueco(p, q, x0, y0, x1, y1, z, prof, colores):
    """Cavidad rectangular vista desde arriba: piso y las dos paredes interiores visibles, recortadas a la boca."""
    arriba, frente, lado = colores
    boca = _cuadro(q, x0, y0, x1, y1, z)
    zf = z - prof
    p.save()
    p.setClipPath(_camino(boca))
    _poli(p, _cuadro(q, x0, y0, x1, y1, zf), arriba.darker(125))
    _poli(p, [q(x0, y0, zf), q(x1, y0, zf), q(x1, y0, z), q(x0, y0, z)], frente.darker(120))
    _poli(p, [q(x0, y0, zf), q(x0, y1, zf), q(x0, y1, z), q(x0, y0, z)], lado.darker(105))
    p.restore()
    _poli(p, boca, None, lado.darker(170))


def _cil(p, cx, arriba, abajo, r, rv, colores=None, borde=None):
    """Cilindro vertical con borde elegible (el de iconos.py siempre lo bordea en azul)."""
    tapa, cuerpo_color = colores or (AZUL_ARRIBA, AZUL_FRENTE)
    cuerpo = QPainterPath()
    cuerpo.moveTo(cx - r, arriba)
    cuerpo.lineTo(cx - r, abajo)
    cuerpo.arcTo(QRectF(cx - r, abajo - rv, 2 * r, 2 * rv), 180, 180)
    cuerpo.lineTo(cx + r, arriba)
    p.setPen(QPen(borde or AZUL_BORDE, 0.9))
    p.setBrush(cuerpo_color)
    p.drawPath(cuerpo)
    p.setBrush(tapa)
    p.drawEllipse(QRectF(cx - r, arriba - rv, 2 * r, 2 * rv))


def _esfera_c(p, cx, cy, r, claro, medio, oscuro, borde):
    g = QRadialGradient(QPointF(cx - r * 0.35, cy - r * 0.4), r * 1.35)
    g.setColorAt(0, claro)
    g.setColorAt(0.5, medio)
    g.setColorAt(1, oscuro)
    p.setPen(QPen(borde, 0.9))
    p.setBrush(QBrush(g))
    p.drawEllipse(QPointF(cx, cy), r, r)


def _tubo(p, puntos, ancho, colores=None):
    """Sólido tubular que sigue una polilínea (borde, cuerpo y un brillo arriba)."""
    arriba, frente = colores or (AZUL_ARRIBA, AZUL_FRENTE)
    poli = QPolygonF(puntos)
    for color, a in ((AZUL_BORDE, ancho + 1.8), (frente, ancho)):
        p.setPen(QPen(color, a, Qt.SolidLine, Qt.FlatCap, Qt.RoundJoin))
        p.setBrush(Qt.NoBrush)
        p.drawPolyline(poli)
    p.save()
    p.translate(-ancho * 0.16, -ancho * 0.22)
    p.setPen(QPen(arriba, ancho * 0.32, Qt.SolidLine, Qt.FlatCap, Qt.RoundJoin))
    p.drawPolyline(poli)
    p.restore()


def _muestras(camino, t0, t1, n=40):
    return [camino.pointAtPercent(t0 + (t1 - t0) * i / n) for i in range(n + 1)]


def _a_plano(p, o, pu, pv, s=10.0):
    """Pasa a coordenadas locales (0..s, 0..s) del paralelogramo o→pu, o→pv (hacer p.save() antes)."""
    p.setTransform(QTransform((pu.x() - o.x()) / s, (pu.y() - o.y()) / s, (pv.x() - o.x()) / s,
                              (pv.y() - o.y()) / s, o.x(), o.y()), True)


def _cara_malla(p, c0, c1, c2, c3, relleno, n=2, borde=None):
    """Cuadrilátero dividido en n×n celdas con su diagonal: los triángulos de una malla."""
    borde = borde or BORDE_MALLA
    _poli(p, [c0, c1, c2, c3], relleno, borde, 0.9)
    pt = lambda u, v: (c0 + (c1 - c0) * u) + ((c3 + (c2 - c3) * u) - (c0 + (c1 - c0) * u)) * v  # noqa: E731
    p.setPen(QPen(borde, 0.6))
    for i in range(1, n):
        p.drawLine(pt(i / n, 0), pt(i / n, 1))
        p.drawLine(pt(0, i / n), pt(1, i / n))
    for i in range(n):
        for j in range(n):
            p.drawLine(pt(i / n, j / n), pt((i + 1) / n, (j + 1) / n))


def _caja_malla(p, q, a, b, h, colores=None, n=2, borde=None):
    arriba, frente, lado = colores or MALLA
    _cara_malla(p, q(0, b, h), q(a, b, h), q(a, b, 0), q(0, b, 0), frente, n, borde)
    _cara_malla(p, q(a, b, h), q(a, 0, h), q(a, 0, 0), q(a, b, 0), lado, n, borde)
    _cara_malla(p, q(0, 0, h), q(a, 0, h), q(a, b, h), q(0, b, h), arriba, n, borde)


def _esfera_malla(p, cx, cy, r, lados=8):
    """Esfera facetada: anillo exterior + anillo interior girado + centro, todo en triángulos."""
    ext = _regular(cx, cy, r, lados, -90)
    inte = _regular(cx - r * 0.12, cy - r * 0.12, r * 0.55, lados, -90 + 180 / lados)
    g = QRadialGradient(QPointF(cx - r * 0.35, cy - r * 0.4), r * 1.4)
    g.setColorAt(0, MALLA[0])
    g.setColorAt(1, MALLA[2])
    p.setPen(QPen(BORDE_MALLA, 0.9))
    p.setBrush(QBrush(g))
    p.drawPolygon(QPolygonF(ext))
    p.setPen(QPen(BORDE_MALLA, 0.6))
    c = QPointF(cx - r * 0.12, cy - r * 0.12)
    for k in range(lados):
        p.drawLine(ext[k], inte[k])
        p.drawLine(ext[(k + 1) % lados], inte[k])
        p.drawLine(inte[k], inte[(k + 1) % lados])
        p.drawLine(inte[k], c)
    return ext


def _eje(p, x0, y0, x1, y1, color=None):
    lapiz = QPen(color or EJE, 1.7, Qt.SolidLine, Qt.FlatCap)
    lapiz.setDashPattern([5, 1.6, 1.2, 1.6])
    p.setPen(lapiz)
    p.drawLine(QPointF(x0, y0), QPointF(x1, y1))


def _arista(p, a, b, ancho=2.4):
    """Arista de referencia (dato de entrada): trazo azul oscuro grueso."""
    p.setPen(QPen(AZUL_BORDE, ancho, Qt.SolidLine, Qt.RoundCap))
    p.drawLine(a, b)


def _punto(p, x, y, r=2.9):
    """Punto de construcción creado: amarillo con borde oscuro."""
    p.setPen(QPen(BORDE_PUNTO, 1.2))
    p.setBrush(PUNTO)
    p.drawEllipse(QPointF(x, y), r, r)


def _punto_dato(p, x, y, r=2.1):
    """Punto que se elige como dato de entrada: gris oscuro."""
    p.setPen(Qt.NoPen)
    p.setBrush(GRIS_OSCURO)
    p.drawEllipse(QPointF(x, y), r, r)


def _plano_q(p, esquinas, relleno=None, borde=None):
    _poli(p, esquinas, relleno or PLANO, borde or BORDE_PLANO, 0.9)


def _hoja(p, x0, y0, x1, y1, d=5.0):
    """Hoja de papel con la esquina doblada."""
    p.setPen(QPen(GRIS_OSCURO, 1.1))
    p.setBrush(QColor("#ffffff"))
    p.drawPolygon(QPolygonF([QPointF(x0, y0), QPointF(x1 - d, y0), QPointF(x1, y0 + d), QPointF(x1, y1),
                             QPointF(x0, y1)]))
    p.drawPolyline(QPolygonF([QPointF(x1 - d, y0), QPointF(x1 - d, y0 + d), QPointF(x1, y0 + d)]))


def _guiones(p, color, ancho=1.1, patron=(2.2, 1.8)):
    lapiz = QPen(color, ancho, Qt.SolidLine, Qt.FlatCap)
    lapiz.setDashPattern(list(patron))
    p.setPen(lapiz)
    p.setBrush(Qt.NoBrush)


def _cursor(p, x, y, s=1.0):
    """Flecha del mouse con la punta en (x, y)."""
    pts = [(0, 0), (0, 11), (2.6, 8.4), (4.6, 12.6), (6.2, 11.8), (4.3, 7.8), (7.8, 7.6)]
    p.setPen(QPen(GRIS_OSCURO, 0.9))
    p.setBrush(QColor("#ffffff"))
    p.drawPolygon(QPolygonF([QPointF(x + dx * s, y + dy * s) for dx, dy in pts]))


def _glifo_union(p, cx, cy, r=4.2):
    """Símbolo de unión (origen de unión): disco blanco con cruz y centro."""
    p.setPen(QPen(GRIS_OSCURO, 1.3))
    p.setBrush(QColor("#ffffff"))
    p.drawEllipse(QPointF(cx, cy), r, r)
    p.setPen(QPen(GRIS_OSCURO, 1.0))
    p.drawLine(QPointF(cx - r, cy), QPointF(cx + r, cy))
    p.drawLine(QPointF(cx, cy - r), QPointF(cx, cy + r))
    p.setPen(Qt.NoPen)
    p.setBrush(AZUL_LADO)
    p.drawEllipse(QPointF(cx, cy), r * 0.38, r * 0.38)


def _doble_flecha(p, x0, y0, x1, y1, color=None, ancho=1.4, punta=3.6):
    xm, ym = (x0 + x1) / 2, (y0 + y1) / 2
    _flecha(p, xm, ym, x0, y0, color or GRIS_OSCURO, ancho, punta)
    _flecha(p, xm, ym, x1, y1, color or GRIS_OSCURO, ancho, punta)


def _onda(a, b, amp):
    """Cúbica de a a b con una onda en S de amplitud vertical `amp`."""
    c = QPainterPath(a)
    d = b - a
    c.cubicTo(a + d / 3 + QPointF(0, -amp), a + d * 2 / 3 + QPointF(0, amp), b)
    return c


def _lamina(p, a, b, c, d, amp=3.0, colores=None, borde=None):
    """Lámina (superficie) de 4 esquinas con los lados a→b y d→c ondulados igual."""
    arriba = colores or SUP[1]
    camino = _onda(a, b, amp)
    camino.lineTo(c)
    camino.connectPath(_onda(d, c, amp).toReversed())
    camino.closeSubpath()
    g = QLinearGradient(a, c)
    g.setColorAt(0, SUP[0] if colores is None else colores.lighter(115))
    g.setColorAt(1, arriba)
    p.setPen(QPen(borde or BORDE_SUP, 1.0))
    p.setBrush(QBrush(g))
    p.drawPath(camino)
    return camino


# ================================================================ SÓLIDO / CREAR
def _barrido(p):
    c = QPainterPath(QPointF(5, 27))
    c.cubicTo(5, 13, 13, 8, 27.5, 8)
    _guion(p, GRIS_OSCURO, 1.1)
    p.drawPath(c)                                         # trayectoria
    _tubo(p, _muestras(c, 0.3, 1.0), 6.5)
    p.setPen(QPen(AZUL_BORDE, 0.9))
    p.setBrush(AZUL_ARRIBA)
    p.drawEllipse(QRectF(26, 3.8, 3.2, 8.4))              # cara final = perfil
    _guiones(p, GRIS_OSCURO, 1.2)
    p.drawEllipse(QRectF(1.2, 25.3, 7.6, 3.4))            # perfil de boceto al inicio
    _ptos(p, [(5, 27)], 2.6)


def _solevacion(p):
    elipse = QRectF(10, 3.8, 12, 6.4)                     # perfil de arriba: un círculo
    izq, der, abajo, atras = QPointF(7.3, 23), QPointF(24.7, 23), QPointF(16, 28), QPointF(16, 18)
    cara = QPainterPath(QPointF(10, 7))
    cara.arcTo(elipse, 180, 90)
    cara.lineTo(abajo)
    cara.lineTo(izq)
    cara.closeSubpath()
    p.setPen(QPen(AZUL_BORDE, 0.9))
    p.setBrush(AZUL_FRENTE)
    p.drawPath(cara)
    cara = QPainterPath(QPointF(16, 10.2))
    cara.arcTo(elipse, 270, 90)
    cara.lineTo(der)
    cara.lineTo(abajo)
    cara.closeSubpath()
    p.setBrush(AZUL_LADO)
    p.drawPath(cara)
    p.setBrush(AZUL_ARRIBA)
    p.drawEllipse(elipse)
    _guiones(p, GRIS_OSCURO, 1.0)                         # aristas ocultas del perfil cuadrado de abajo
    p.drawPolyline(QPolygonF([izq, atras, der]))


def _nervio(p):
    q = _q(14.3, 16.5)
    _caja_en(p, q, 0, 0, 0, 16, 12, 3, GRISES, BORDE_GRIS)
    _caja_en(p, q, 0, 0, 3, 16, 3, 12, GRISES, BORDE_GRIS)
    _poli(p, [q(9, 3, 3), q(9, 12, 3), q(9, 3, 15)], AZUL_LADO)
    _poli(p, [q(6.5, 3, 15), q(9, 3, 15), q(9, 12, 3), q(6.5, 12, 3)], AZUL_ARRIBA)


def _red(p):
    q = _q(16, 11.5)
    _caja_en(p, q, 0, 0, 0, 18, 18, 2, GRISES, BORDE_GRIS)
    _caja_en(p, q, 8.1, 0, 2, 1.8, 8.1, 7)
    _caja_en(p, q, 0, 8.1, 2, 18, 1.8, 7)
    _caja_en(p, q, 8.1, 9.9, 2, 1.8, 8.1, 7)


def _labio(p):
    a = b = 16
    h, e, m, s = 8, 3.2, 1.5, 3.0          # alto de la pared, espesor, retiro del labio y alto del labio
    q = _q(16, 13.5)
    _caja_en(p, q, 0, 0, 0, a, b, h, GRISES, BORDE_GRIS)
    _poli(p, [q(m, b - m, h), q(a - m, b - m, h), q(a - m, b - m, h + s), q(m, b - m, h + s)], AZUL_FRENTE)
    _poli(p, [q(a - m, m, h), q(a - m, b - m, h), q(a - m, b - m, h + s), q(a - m, m, h + s)], AZUL_LADO)
    anillo = _camino(_cuadro(q, m, m, a - m, b - m, h + s))
    anillo.addPath(_camino(_cuadro(q, e, e, a - e, b - e, h + s)))
    anillo.setFillRule(Qt.OddEvenFill)
    p.setPen(QPen(AZUL_BORDE, 0.9))
    p.setBrush(AZUL_ARRIBA)
    p.drawPath(anillo)
    _hueco(p, q, e, e, a - e, b - e, h + s, h + s - 2, OSCUROS)


def _repujado(p):
    a, b, h = 17, 17, 5
    q = _q(*_centro(a, b, h))
    _caja_en(p, q, 0, 0, 0, a, b, h, GRISES, BORDE_GRIS)
    for dz, color in ((0, AZUL_BORDE), (0.8, AZUL_LADO), (1.6, AZUL_LADO), (2.6, AZUL_ARRIBA)):
        p.save()
        _a_plano(p, q(1.5, 1.5, h + dz), q(15.5, 1.5, h + dz), q(1.5, 15.5, h + dz), 14)
        _letras(p, QRectF(0, -1, 14, 16), "A", color, 15)
        p.restore()


def _saliente(p):
    q = _q(16, 11.2)
    _caja_en(p, q, 0, 0, 0, 17, 17, 3, GRISES, BORDE_GRIS)
    base = q(8.5, 8.5, 3)
    _cil(p, base.x(), base.y() - 10, base.y(), 5.2, 2.9)
    p.setPen(QPen(AZUL_BORDE, 0.9))
    p.setBrush(QColor("#173f66"))
    p.drawEllipse(QRectF(base.x() - 2.4, base.y() - 10 - 1.35, 4.8, 2.7))   # agujero del tornillo


def _encaje_presion(p):
    q = _q(12, 17.5)
    _caja_en(p, q, 0, 0, 0, 14, 8, 4, GRISES, BORDE_GRIS)
    _caja_en(p, q, 5, 2, 4, 2.4, 4, 15)                                  # brazo flexible
    a, b, c = (7.4, 19), (13.5, 14), (7.4, 14)                            # gancho (x, z)
    _poli(p, [q(a[0], 2, a[1]), q(b[0], 2, b[1]), q(b[0], 6, b[1]), q(a[0], 6, a[1])], AZUL_ARRIBA)
    _poli(p, [q(a[0], 6, a[1]), q(b[0], 6, b[1]), q(c[0], 6, c[1])], AZUL_FRENTE)


def _agujero(p):
    q = _caja_c(p, 18, 18, 9)
    c = q(9, 9, 9)
    boca = QRectF(c.x() - 6, c.y() - 3.5, 12, 7)
    p.setPen(QPen(AZUL_BORDE, 0.9))
    p.setBrush(AZUL_LADO)
    p.drawEllipse(boca)
    p.save()
    camino = QPainterPath()
    camino.addEllipse(boca)
    p.setClipPath(camino)
    p.setPen(Qt.NoPen)
    p.setBrush(QColor("#163f66"))
    p.drawEllipse(boca.translated(0, 4.2))
    p.restore()


def _rosca(p):
    cx, arriba, abajo, r, rv = 16, 7, 25, 8.5, 3.2
    _cilindro(p, cx, arriba, abajo, r, rv)
    cuerpo = QPainterPath()
    cuerpo.addRect(QRectF(cx - r, arriba, 2 * r, abajo - arriba))
    cuerpo.addEllipse(QRectF(cx - r, abajo - rv, 2 * r, 2 * rv))
    cuerpo.setFillRule(Qt.WindingFill)
    tapa = QPainterPath()
    tapa.addEllipse(QRectF(cx - r, arriba - rv, 2 * r, 2 * rv))
    p.save()
    p.setClipPath(cuerpo.subtracted(tapa))
    p.setPen(QPen(AZUL_BORDE, 1.3))
    p.setBrush(Qt.NoBrush)
    paso, y = 3.6, arriba + 1.0
    while y < abajo + rv + paso:
        c = QPainterPath(QPointF(cx - r, y))
        c.quadTo(cx, y + 2 * rv - paso / 4, cx + r, y - paso / 2)
        p.drawPath(c)
        y += paso
    p.restore()


def _bobina(p):
    cx, r, rv, paso, y0, vueltas, n = 16, 9.5, 3.0, 7.2, 5.5, 2.9, 180
    tramos = []
    for i in range(n + 1):
        t = vueltas * 2 * math.pi * i / n
        punto = QPointF(cx + r * math.cos(t), y0 + paso * t / (2 * math.pi) + rv * math.sin(t))
        adelante = math.sin(t) >= 0
        if tramos and tramos[-1][0] == adelante:
            tramos[-1][1].append(punto)
        else:
            tramos.append((adelante, ([tramos[-1][1][-1]] if tramos else []) + [punto]))
    for capa in (False, True):
        for adelante, puntos in tramos:
            if adelante != capa:
                continue
            for color, ancho in ((AZUL_BORDE, 3.8), (AZUL_FRENTE if adelante else AZUL_LADO, 2.3)):
                p.setPen(QPen(color, ancho, Qt.SolidLine, Qt.FlatCap, Qt.RoundJoin))
                p.drawPolyline(QPolygonF(puntos))


def _tuberia(p):
    c = QPainterPath(QPointF(4.5, 24))
    c.lineTo(12, 24)
    c.quadTo(22, 24, 22, 14)
    c.lineTo(22, 6.5)
    _tubo(p, _muestras(c, 0, 1, 60), 7.0)
    p.setPen(QPen(AZUL_BORDE, 0.9))
    for rect, hueco in ((QRectF(2.6, 19.6, 3.8, 8.8), QRectF(3.6, 21.6, 1.8, 4.8)),
                        (QRectF(17.6, 4.6, 8.8, 3.8), QRectF(19.6, 5.6, 4.8, 1.8))):
        p.setBrush(AZUL_ARRIBA)
        p.drawEllipse(rect)
        p.setBrush(QColor("#163f66"))
        p.drawEllipse(hueco)


def _patron_rectangular_3d(p):
    q = _q(12.5, 10)
    for i, j in sorted(((i, j) for i in range(3) for j in range(2)), key=lambda c: c[0] + c[1]):
        original = i == 0 and j == 0
        _caja_en(p, q, i * 8, j * 8, 0, 5, 5, 5, None if original else FANTASMA,
                 None if original else BORDE_FANTASMA)


def _patron_circular_3d(p):
    cx, cy, rx, ry = 16, 19, 10.5, 6.2
    _eje(p, 16, 2.5, 16, 29.5)
    postes = sorted((math.radians(90 + 60 * k) for k in range(6)), key=math.sin)
    for a in postes:
        x, y = cx + rx * math.cos(a), cy + ry * math.sin(a)
        original = abs(a - math.radians(90)) < 1e-6
        _cil(p, x, y - 6, y, 2.7, 1.5, None if original else (FANTASMA[0], FANTASMA[1]),
             None if original else BORDE_FANTASMA)


def _patron_ruta(p):
    c = _curva_por([(5, 26), (12, 14), (20, 21), (27, 9)])
    _guion(p, GRIS_OSCURO, 1.1)
    p.drawPath(c)
    for k, t in enumerate((0.06, 0.37, 0.65, 0.94)):
        o = c.pointAtPercent(t)
        _caja(p, 4.5, 4.5, 4.5, o.x(), o.y() - 2.2, 1.0, _azules() if k == 0 else FANTASMA,
              AZUL_BORDE if k == 0 else BORDE_FANTASMA)


def _simetria_3d(p):
    q = _q(13.8, 13.75)
    _caja_en(p, q, 0, 1, 0, 6, 10, 9)
    _plano_q(p, [q(8.5, -2, -1), q(8.5, 14, -1), q(8.5, 14, 13), q(8.5, -2, 13)])
    _caja_en(p, q, 11, 1, 0, 6, 10, 9, FANTASMA, BORDE_FANTASMA)


def _engrosar(p):
    arriba = QPainterPath(QPointF(3, 12))
    arriba.cubicTo(10, 4, 17, 16, 24, 8)
    abajo = arriba.translated(0, 8)
    cuerpo = QPainterPath(arriba)
    cuerpo.lineTo(24, 16)
    cuerpo.connectPath(abajo.toReversed())
    cuerpo.closeSubpath()
    g = QLinearGradient(QPointF(0, 8), QPointF(0, 22))
    g.setColorAt(0, AZUL_FRENTE)
    g.setColorAt(1, AZUL_LADO)
    p.setPen(QPen(AZUL_BORDE, 0.9))
    p.setBrush(QBrush(g))
    p.drawPath(cuerpo)
    p.setPen(QPen(QColor("#e08a2e"), 2.6, Qt.SolidLine, Qt.RoundCap))   # la superficie original
    p.setBrush(Qt.NoBrush)
    p.drawPath(arriba)
    _doble_flecha(p, 28.5, 6.5, 28.5, 18.5)


def _relleno_contorno(p):
    a, b = QPainterPath(), QPainterPath()
    a.addEllipse(QPointF(12, 16), 9.5, 9.5)
    b.addEllipse(QPointF(20, 16), 9.5, 9.5)
    p.setPen(QPen(AZUL_BORDE, 0.9))
    p.setBrush(AZUL_FRENTE)
    p.drawPath(a.intersected(b))
    p.setPen(QPen(BORDE_PLANO, 1.5))
    p.setBrush(Qt.NoBrush)
    p.drawPath(a)
    p.drawPath(b)


def _cuerpo_envolvente(p):
    a = b = h = 13
    cx, cy = _centro(a, b, h)
    q = _q(cx, cy)
    _guiones(p, AZUL_BORDE, 0.9)
    for fin in (q(a, 0, 0), q(0, b, 0), q(0, 0, h)):
        p.drawLine(q(0, 0, 0), fin)
    base, tope = q(6.5, 6.5, 0), q(6.5, 6.5, 10)
    _cil(p, base.x(), tope.y(), base.y(), 5, 2.8, (GRISES[0], GRISES[1]), BORDE_GRIS)
    _caja(p, a, b, h, cx, cy, 1.0, (QColor(159, 207, 245, 70), QColor(74, 155, 224, 70), QColor(43, 120, 194, 70)),
          AZUL_BORDE)


def _operacion_base(p):
    _guiones(p, GRIS_OSCURO, 1.2)
    p.drawRoundedRect(QRectF(3, 3, 26, 26), 4, 4)
    _caja_c(p, 11, 11, 11)


def _derivar(p):
    _hoja(p, 2.5, 2.5, 16, 18, 4)
    _caja(p, 5, 5, 5, 9, 11)
    _flecha(p, 13.5, 16, 19, 21.5, AZUL_LADO, 2.0, 4.5)
    _caja(p, 8, 8, 8, 23, 21)


def _crear_forma(p):
    q = _q(16, 16)
    s = 12
    cubo = _hexagono(q, s, s, s)
    pts = [q(x, y, z) for x, y, z in ((1.5, 1.5, s - 1.5), (s - 1.5, 1.5, s - 1.5), (s - 1, 0.5, 1.5),
                                      (s - 1.5, s - 1.5, 0.5), (0.5, s - 1, 1.5), (1.5, s - 1.5, s - 1.5))]
    blob = QPainterPath((pts[-1] + pts[0]) / 2)
    for k in range(6):
        blob.quadTo(pts[k], (pts[k] + pts[(k + 1) % 6]) / 2)
    g = QRadialGradient(QPointF(13, 11), 17)
    g.setColorAt(0, QColor("#efe6fd"))
    g.setColorAt(0.55, QColor("#b79fe8"))
    g.setColorAt(1, QColor("#7d5fc0"))
    p.setPen(QPen(VIOLETA, 0.9))
    p.setBrush(QBrush(g))
    p.drawPath(blob)
    _guiones(p, VIOLETA, 0.9)
    p.drawPolygon(QPolygonF(cubo))
    for fin in (q(0, s, s), q(s, 0, s), q(s, s, 0)):
        p.drawLine(q(s, s, s), fin)
    _ptos(p, [(v.x(), v.y()) for v in cubo + [q(s, s, s)]], 2.6, VIOLETA)


# ================================================================ MODIFICAR
def _pulsar_tirar(p):
    _caja(p, 14, 14, 7, 16, 15, 1.0, (AZUL_SEL, AZUL_FRENTE, AZUL_LADO))
    _doble_flecha(p, 16, 2.5, 16, 14, GRIS_OSCURO, 2.0, 4.5)


def _arista_viva(p, curva):
    a, b, h, r = 14, 14, 12, 6.5
    q = _q(*_centro(a, b, h))
    if curva:
        perfil = [(b - r + r * math.sin(t), h - r + r * math.cos(t))
                  for t in (math.pi / 2 * i / 12 for i in range(13))]
    else:
        perfil = [(b - r, h), (b, h - r)]
    _poli(p, [q(0, b, 0), q(a, b, 0), q(a, b, h - r), q(0, b, h - r)], AZUL_FRENTE)
    _poli(p, [q(a, 0, 0), q(a, b, 0)] + [q(a, y, z) for y, z in reversed(perfil)] + [q(a, 0, h)], AZUL_LADO)
    _poli(p, [q(0, 0, h), q(a, 0, h), q(a, b - r, h), q(0, b - r, h)], AZUL_ARRIBA)
    banda = [q(0, y, z) for y, z in perfil] + [q(a, y, z) for y, z in reversed(perfil)]
    if curva:
        g = QLinearGradient(q(a / 2, b - r, h), q(a / 2, b, h - r))
        g.setColorAt(0, AZUL_ARRIBA)
        g.setColorAt(0.35, QColor("#e6f3fe"))
        g.setColorAt(1, AZUL_FRENTE)
        _poli(p, banda, QBrush(g))
    else:
        _poli(p, banda, QColor("#c6e2fa"))


def _vaciado(p):
    a = b = 18
    h, e = 11, 2.5
    q = _caja_c(p, a, b, h)
    _hueco(p, q, e, e, a - e, b - e, h, h - e, _azules())


def _desmoldeo(p):
    a = b = 14
    h, d = 12, 3.5
    q = _q(14.5, 13)
    _poli(p, [q(0, b, 0), q(a, b, 0), q(a - d, b - d, h), q(d, b - d, h)], AZUL_FRENTE)
    _poli(p, [q(a, 0, 0), q(a, b, 0), q(a - d, b - d, h), q(a - d, d, h)], AZUL_LADO)
    _poli(p, _cuadro(q, d, d, a - d, b - d, h), AZUL_ARRIBA)
    _guion(p, GRIS_OSCURO, 1.1)
    p.drawLine(q(a, 0, 0), q(a, 0, h + 2))                 # la vertical original
    _trazo(p, GRIS_OSCURO, 1.1)
    arco = QPainterPath(QPointF(26.6, 12))
    arco.quadTo(25, 11.6, 23.1, 12.9)
    p.drawPath(arco)


def _escala_3d(p):
    s, c = 12, 5
    q = _q(16, 16)
    _guion(p, GRIS_OSCURO, 1.1)
    p.drawPolygon(QPolygonF(_hexagono(q, s, s, s)))
    for fin in (q(0, s, s), q(s, 0, s), q(s, s, 0)):
        p.drawLine(q(s, s, s), fin)
    _caja_en(p, q, 0, s - c, 0, c, c, c)
    _flecha(p, *_xy(q(c, s - c, c)), *_xy(q(s - 0.8, 0.8, s - 0.8)), GRIS_OSCURO, 1.8, 4.5)


def _xy(punto):
    return punto.x(), punto.y()


def _desfase_cara(p):
    a = b = h = 12
    q = _q(13.85, 14.75)
    _caja_en(p, q, 0, 0, 0, a, b, h, (AZUL_ARRIBA, AZUL_FRENTE, QColor("#8cc6f3")))
    _guiones(p, AZUL_BORDE, 1.0)
    p.setBrush(QColor(159, 207, 245, 110))
    p.drawPolygon(QPolygonF([q(17, 0, 0), q(17, b, 0), q(17, b, h), q(17, 0, h)]))
    for y, z in ((3.5, 8.5), (8.5, 3.5)):
        _flecha(p, *_xy(q(a, y, z)), *_xy(q(16.5, y, z)), GRIS_OSCURO, 1.5, 3.6)


def _reemplazar_cara(p):
    q = _q(16, 16)
    _caja_en(p, q, 0, 0, 0, 12, 12, 5, (AZUL_SEL, AZUL_FRENTE, AZUL_LADO))
    _flecha(p, *_xy(q(6, 6, 5)), *_xy(q(6, 6, 10)), GRIS_OSCURO, 1.6, 4)
    z = 11
    _lamina(p, q(-1, -1, z), q(13, -1, z), q(13, 13, z), q(-1, 13, z), 2.4)


def _dividir_cara(p):
    a, b, h = 14, 14, 12
    q = _caja_c(p, a, b, h)
    _poli(p, [q(0, b, 0), q(a / 2, b, 0), q(a / 2, b, h), q(0, b, h)], AZUL_SEL)
    p.setPen(QPen(NARANJA, 2.0, Qt.SolidLine, Qt.RoundCap))
    p.drawLine(q(a / 2, b, -1.5), q(a / 2, b, h))


def _dividir_cuerpo(p):
    q = _q(16, 16.5)
    _caja_en(p, q, 0, 0, 0, 13, 13, 5.5)
    _plano_q(p, _cuadro(q, -2, -2, 15, 15, 7.5))
    _caja_en(p, q, 0, 0, 9.5, 13, 13, 5.5)


def _division_silueta(p):
    cx, cy, r = 16, 20, 9.5
    _esfera_c(p, cx, cy, r, AZUL_ARRIBA, AZUL_FRENTE, AZUL_LADO, AZUL_BORDE)
    abajo = QPainterPath()
    abajo.addEllipse(QPointF(cx, cy), r, r)
    tapa = QPainterPath()
    tapa.addRect(QRectF(cx - r - 1, cy - r - 1, 2 * r + 2, r + 1))
    tapa.addEllipse(QRectF(cx - r, cy - 3.3, 2 * r, 6.6))
    tapa.setFillRule(Qt.WindingFill)
    g = QRadialGradient(QPointF(cx - 3, cy), r * 1.3)
    g.setColorAt(0, GRISES[0])
    g.setColorAt(1, GRISES[2])
    p.setPen(QPen(BORDE_GRIS, 0.9))
    p.setBrush(QBrush(g))
    p.drawPath(abajo.subtracted(tapa))
    p.setPen(QPen(NARANJA, 1.8))
    p.setBrush(Qt.NoBrush)
    p.drawArc(QRectF(cx - r, cy - 3.3, 2 * r, 6.6), 180 * 16, 180 * 16)
    _flecha(p, cx, 1.5, cx, 8.8, GRIS_OSCURO, 1.8, 4.2)


def _mover_copiar(p):
    _caja(p, 8, 8, 8, 9.5, 11, 1.0, FANTASMA, BORDE_FANTASMA)
    _caja(p, 8, 8, 8, 22.5, 17, 1.0)
    arco = QPainterPath(QPointF(5, 22))
    arco.quadTo(7, 28.5, 13.5, 27.5)
    _trazo(p, GRIS_OSCURO, 1.8)
    p.drawPath(arco)
    _flecha(p, 12.5, 27.7, 16, 26.8, GRIS_OSCURO, 1.8, 4.2)


def _alinear(p):
    p.setPen(QPen(AZUL_BORDE, 0.9))
    p.setBrush(AZUL_FRENTE)
    p.drawRect(QRectF(17, 7, 11, 20))
    p.setBrush(GRISES[1])
    p.setPen(QPen(BORDE_GRIS, 0.9))
    p.drawRect(QRectF(4, 17, 9, 10))
    _guiones(p, BORDE_GRIS, 1.0)
    p.drawRect(QRectF(4, 7, 9, 10))
    _guiones(p, NARANJA, 1.4, (3, 2))
    p.drawLine(QPointF(2, 7), QPointF(30, 7))
    _flecha(p, 8.5, 16, 8.5, 9.5, GRIS_OSCURO, 1.6, 4)


def _suprimir(p):
    _caja_c(p, 12, 12, 11, FANTASMA, BORDE_FANTASMA)
    p.setPen(QPen(ROJO, 3.6, Qt.SolidLine, Qt.RoundCap))
    p.drawLine(QPointF(8, 8), QPointF(24, 24))
    p.drawLine(QPointF(24, 8), QPointF(8, 24))


def _quitar(p):
    _caja(p, 12, 12, 11, 13.5, 13.5)
    p.setPen(QPen(QColor("#ffffff"), 1.2))
    p.setBrush(ROJO)
    p.drawEllipse(QPointF(23, 23), 6.5, 6.5)
    p.setPen(QPen(QColor("#ffffff"), 2.4, Qt.SolidLine, Qt.FlatCap))
    p.drawLine(QPointF(19.5, 23), QPointF(26.5, 23))


def _material_fisico(p):
    cx, cy, r = 16, 16, 12
    _esfera_c(p, cx, cy, r, QColor("#ffffff"), QColor("#bcc3cb"), QColor("#6e7782"), GRIS_OSCURO)
    madera = QPainterPath()
    madera.addEllipse(QPointF(cx, cy), r, r)
    corte = QPainterPath()
    corte.addPolygon(QPolygonF([QPointF(0, 32), QPointF(32, 0), QPointF(32, 32)]))
    madera = madera.intersected(corte)
    p.setPen(QPen(GRIS_OSCURO, 0.9))
    p.setBrush(QColor("#c98c4f"))
    p.drawPath(madera)
    p.save()
    p.setClipPath(madera)
    p.setPen(QPen(QColor("#8a5526"), 1.0))
    p.setBrush(Qt.NoBrush)
    for rr in (5, 9, 13, 17):
        p.drawEllipse(QPointF(30, 30), rr, rr * 0.8)
    p.restore()


def _aspecto(p):
    _caja(p, 12, 12, 8, 13, 18, 1.0, ROJOS, QColor("#7a1a14"))
    gota = QPainterPath(QPointF(24, 2))
    gota.cubicTo(25.5, 5.5, 29, 8, 29, 11)
    gota.arcTo(QRectF(19, 6, 10, 10), 0, -180)
    gota.cubicTo(19, 8, 22.5, 5.5, 24, 2)
    g = QLinearGradient(QPointF(19, 4), QPointF(29, 16))
    g.setColorAt(0, QColor("#ff8a80"))
    g.setColorAt(1, QColor("#c62828"))
    p.setPen(QPen(QColor("#7a1a14"), 0.9))
    p.setBrush(QBrush(g))
    p.drawPath(gota)
    p.setPen(Qt.NoPen)
    p.setBrush(QColor(255, 255, 255, 190))
    p.drawEllipse(QRectF(21, 9, 2.4, 3.4))


def _administrar_materiales(p):
    _esfera_c(p, 16, 9.5, 7, QColor("#ffffff"), QColor("#bcc3cb"), QColor("#6e7782"), GRIS_OSCURO)
    _esfera_c(p, 9, 21.5, 7, QColor("#f3cf9f"), QColor("#c98c4f"), QColor("#7f4f22"), QColor("#5c3815"))
    _esfera_c(p, 23, 21.5, 7, QColor("#ffb3ab"), QColor("#e04a3c"), QColor("#8e1f17"), QColor("#6a140e"))


def _lista_materiales(p):
    _hoja(p, 5, 3, 27, 29, 5)
    p.setPen(Qt.NoPen)
    p.setBrush(AZUL_LADO)
    p.drawRect(QRectF(5.6, 3.6, 16, 4))
    for k, y in enumerate((11.5, 16.5, 21.5, 26)):
        _caja(p, 2.6, 2.6, 2.6, 9.5, y - 0.6, 1.0)
        p.setPen(QPen(GRIS_OSCURO, 1.3))
        p.drawLine(QPointF(13, y), QPointF(24 - 2 * (k % 2), y))


# ================================================================ CONSTRUIR
def _scu(p):
    o = QPointF(9, 22)
    ux, uy, uz = QPointF(0.959, 0.282), QPointF(0.862, -0.507), QPointF(0, -1)
    for u, v, color in ((ux, uy, PLANO), (ux, uz, PLANO_2), (uy, uz, QColor(255, 224, 150, 200))):
        _plano_q(p, [o, o + u * 8, o + u * 8 + v * 8, o + v * 8], color)
    for u, color in ((ux, ROJO), (uy, VERDE), (uz, AZUL_LADO)):
        fin = o + u * 18.5
        _flecha(p, o.x(), o.y(), fin.x(), fin.y(), color, 2.0, 4.2)
    _punto(p, o.x(), o.y(), 2.4)


def _plano_angulo(p):
    _poli(p, [QPointF(3, 21), QPointF(19, 29), QPointF(28.5, 23.5), QPointF(12.5, 15.5)], GRIS_PLANO,
          BORDE_GRIS_PLANO)
    _plano_q(p, [QPointF(3, 21), QPointF(19, 29), QPointF(23, 16), QPointF(7, 8)])
    _arista(p, QPointF(3, 21), QPointF(19, 29))
    _trazo(p, GRIS_OSCURO, 1.3)
    arco = QPainterPath(QPointF(25.6, 25.2))
    arco.quadTo(25.5, 22.5, 21.3, 22.4)
    p.drawPath(arco)


def _plano_tangente(p):
    y, r = 21.5, 6.5
    cuerpo = QPainterPath()
    cuerpo.addRect(QRectF(6, y - r, 18, 2 * r))
    cuerpo.addEllipse(QRectF(3.4, y - r, 5.2, 2 * r))
    cuerpo.setFillRule(Qt.WindingFill)
    p.setPen(QPen(AZUL_BORDE, 0.9))
    p.setBrush(AZUL_FRENTE)
    p.drawPath(cuerpo.simplified())
    p.setBrush(AZUL_ARRIBA)
    p.drawEllipse(QRectF(21.4, y - r, 5.2, 2 * r))
    _plano_q(p, [QPointF(2, 18.5), QPointF(9, 11.5), QPointF(30, 11.5), QPointF(23, 18.5)])
    _arista(p, QPointF(6, y - r), QPointF(24, y - r), 1.8)


def _plano_medio(p):
    q = _q(16, 16.25)
    _caja_en(p, q, 0, 0, 0, 12, 12, 1.5, GRISES, BORDE_GRIS)
    _plano_q(p, _cuadro(q, -2, -2, 14, 14, 6))
    _caja_en(p, q, 0, 0, 11, 12, 12, 1.5, GRISES, BORDE_GRIS)


def _plano_perpendicular(p):
    q = _q(16, 16)
    _arista(p, q(-9, 0, 0), q(0, 0, 0))
    _plano_q(p, [q(0, -7, -7), q(0, 7, -7), q(0, 7, 7), q(0, -7, 7)])
    _arista(p, q(0, 0, 0), q(10, 0, 0))
    _trazo(p, GRIS_OSCURO, 1.1)
    p.drawPolyline(QPolygonF([q(3, 0, 0), q(3, 0, 3), q(0, 0, 3)]))


def _plano_dos_aristas(p):
    a, b, c, d = QPointF(5, 21), QPointF(13, 8), QPointF(27, 12), QPointF(19, 25)
    _plano_q(p, [a, b, c, d])
    for u, v in ((a, d), (b, c)):
        e = (v - u) * 0.15
        _arista(p, u - e, v + e)


def _plano_tres_puntos(p):
    _plano_q(p, [QPointF(3, 20), QPointF(12, 6), QPointF(29, 12), QPointF(20, 26)])
    pts = [QPointF(9, 18), QPointF(15, 10), QPointF(22, 20)]
    _guiones(p, GRIS_OSCURO, 1.0)
    p.drawPolygon(QPolygonF(pts))
    for v in pts:
        _punto_dato(p, v.x(), v.y(), 2.4)


def _plano_ruta(p):
    _trazo(p, GRIS_OSCURO, 1.6)
    p.drawPath(_curva_por([(2.5, 9), (9.5, 12.4), (16, 16)]))
    c, ys = QPointF(16, 16), QPointF(-0.866, 0.5) * 7
    zs = QPointF(0, -7)
    _plano_q(p, [c - ys - zs, c + ys - zs, c + ys + zs, c - ys + zs])
    _trazo(p, GRIS_OSCURO, 1.6)
    p.drawPath(_curva_por([(16, 16), (22.5, 19.8), (27, 27)]))
    _punto(p, 16, 16, 2.4)


def _eje_cilindro(p):
    _cilindro(p, 16, 8, 24, 8, 3)
    _eje(p, 16, 1.5, 16, 30.5)


def _eje_perpendicular(p):
    q = _q(16, 15)
    _poli(p, _cuadro(q, 0, 0, 14, 14, 0), GRIS_PLANO, BORDE_GRIS_PLANO)
    c = q(7, 7, 0)
    _eje(p, c.x(), c.y() + 7, c.x(), 2)
    _trazo(p, GRIS_OSCURO, 1.1)
    p.drawPolyline(QPolygonF([q(9.5, 7, 0), q(9.5, 7, 2.5), q(7, 7, 2.5)]))
    _punto_dato(p, c.x(), c.y(), 2.2)


def _eje_dos_planos(p):
    q = _q(16, 16)
    _plano_q(p, [q(-8, 0, -6), q(8, 0, -6), q(8, 0, 6), q(-8, 0, 6)])
    _plano_q(p, [q(0, -8, -6), q(0, 8, -6), q(0, 8, 6), q(0, -8, 6)], PLANO_2)
    _eje(p, *_xy(q(0, 0, -14)), *_xy(q(0, 0, 14)))


def _eje_dos_puntos(p):
    _eje(p, 3, 27, 29, 5)
    _punto_dato(p, 10, 21, 2.8)
    _punto_dato(p, 22, 11, 2.8)


def _eje_arista(p):
    a = b = h = 12
    q = _caja_c(p, a, b, h)
    _arista(p, q(0, b, h), q(a, b, h), 2.6)
    _eje(p, *_xy(q(-5, b, h)), *_xy(q(a + 5, b, h)))


def _punto_vertice(p):
    a = b = h = 13
    q = _caja_c(p, a, b, h)
    _punto(p, *_xy(q(a, b, h)), 3.4)


def _punto_dos_aristas(p):
    _arista(p, QPointF(4, 24), QPointF(28, 10))
    _arista(p, QPointF(8, 5), QPointF(22, 28))
    _punto(p, 15.1, 17.5, 3.3)


def _punto_tres_planos(p):
    o = QPointF(16, 17)
    ex, ey, ez = QPointF(0.866, 0.5), QPointF(-0.866, 0.5), QPointF(0, -1)
    for u, v, color in ((ex * 8, ey * 8, QColor(255, 224, 150, 190)), (ex * 5.5, ez * 10, PLANO),
                        (ey * 5.5, ez * 10, PLANO_2)):
        _plano_q(p, [o - u - v, o + u - v, o + u + v, o - u + v], color)
    _punto(p, o.x(), o.y(), 3.3)


def _punto_centro(p):
    _cil(p, 16, 13, 21, 12, 6.5)
    _guiones(p, GRIS_OSCURO, 1.2)
    p.drawLine(QPointF(16, 13), QPointF(28, 13))
    _punto(p, 16, 13, 3.1)


def _punto_arista_plano(p):
    q = _q(16, 12)
    _arista(p, QPointF(13, 3), QPointF(16, 16))
    _plano_q(p, _cuadro(q, 0, 0, 14, 14, 0))
    _guiones(p, AZUL_BORDE, 1.6)
    p.drawLine(QPointF(16.2, 17), QPointF(17.5, 23))
    _arista(p, QPointF(17.5, 23), QPointF(19, 29.5))
    _punto(p, 16, 16, 3.1)


def _punto_ruta(p):
    c = _curva_por([(3, 26), (10, 12), (21, 20), (29, 7)])
    _trazo(p, GRIS_OSCURO, 1.6)
    p.drawPath(c)
    _ptos(p, [(3, 26)], 3.2)
    m = c.pointAtPercent(0.62)
    _punto(p, m.x(), m.y(), 3.2)
    a = QPainterPath(QPointF(7, 27.5))
    a.quadTo(12, 31, 16, 25.5)
    _trazo(p, NARANJA, 1.3)
    p.drawPath(a)


# ================================================================ INSPECCIONAR
def _interferencia(p):
    qa, qb = _q(11, 12), _q(21, 17.5)
    _caja_en(p, qa, 0, 0, 0, 11, 11, 11, GRISES, BORDE_GRIS)
    _caja_en(p, qb, 0, 0, 0, 10, 10, 10, (QColor(200, 225, 248, 230), QColor(120, 175, 230, 230),
                                          QColor(80, 140, 205, 230)))
    choque = _camino(_hexagono(qa, 11, 11, 11)).intersected(_camino(_hexagono(qb, 10, 10, 10)))
    p.setPen(QPen(QColor("#8e1f17"), 1.0))
    p.setBrush(QColor(214, 69, 69, 230))
    p.drawPath(choque)


def _curvatura_peine(p):
    c = QPainterPath(QPointF(3, 24))
    c.cubicTo(9, 2, 19, 30, 29, 9)
    puntas, n, e = [], 26, 0.012
    p.setPen(QPen(AZUL_FRENTE, 0.8))
    for i in range(n + 1):
        t = min(max(i / n, e), 1 - e)
        a, b, d = c.pointAtPercent(t - e), c.pointAtPercent(t), c.pointAtPercent(t + e)
        u, v = b - a, d - b
        cruz = u.x() * v.y() - u.y() * v.x()
        k = 2 * cruz / max(math.hypot(u.x(), u.y()) * math.hypot(v.x(), v.y()) * math.hypot(*_xy(d - a)), 1e-9)
        tan = d - a
        largo = math.hypot(tan.x(), tan.y())
        normal = QPointF(tan.y() / largo, -tan.x() / largo)
        punta = b + normal * (k * 40)
        p.drawLine(b, punta)
        puntas.append(punta)
    p.setPen(QPen(ROJO, 1.1))
    p.drawPolyline(QPolygonF(puntas))
    _trazo(p, GRIS_OSCURO, 1.8)
    p.drawPath(c)


def _cebra(p):
    esfera = QPainterPath()
    esfera.addEllipse(QPointF(16, 16), 12, 12)
    p.setPen(Qt.NoPen)
    p.setBrush(QColor("#ffffff"))
    p.drawPath(esfera)
    p.save()
    p.setClipPath(esfera)
    p.setPen(QPen(QColor("#1e1e1e"), 2.6))
    p.setBrush(Qt.NoBrush)
    for rr in range(6, 44, 6):
        p.drawEllipse(QPointF(3, 31), rr, rr * 0.82)
    p.restore()
    p.setPen(QPen(GRIS_OSCURO, 1.0))
    p.setBrush(Qt.NoBrush)
    p.drawPath(esfera)


def _mapa_entorno(p):
    esfera = QPainterPath()
    esfera.addEllipse(QPointF(16, 16), 12, 12)
    cielo = QLinearGradient(QPointF(0, 4), QPointF(0, 17))
    cielo.setColorAt(0, QColor("#3d8fd8"))
    cielo.setColorAt(1, QColor("#e8f4ff"))
    p.setPen(Qt.NoPen)
    p.setBrush(QBrush(cielo))
    p.drawPath(esfera)
    p.save()
    p.setClipPath(esfera)
    suelo = QLinearGradient(QPointF(0, 17), QPointF(0, 28))
    suelo.setColorAt(0, QColor("#a5835a"))
    suelo.setColorAt(1, QColor("#4d3a22"))
    horizonte = QPainterPath(QPointF(3, 18))
    horizonte.quadTo(16, 14, 29, 18)
    horizonte.lineTo(29, 30)
    horizonte.lineTo(3, 30)
    p.setBrush(QBrush(suelo))
    p.drawPath(horizonte)
    p.setBrush(QColor("#fff6c8"))
    p.drawEllipse(QPointF(11, 9.5), 2.6, 2.6)
    p.restore()
    p.setPen(QPen(GRIS_OSCURO, 1.0))
    p.setBrush(Qt.NoBrush)
    p.drawPath(esfera)


def _angulo_desmoldeo(p):
    a = b = 14
    h, d = 11, 3.5
    q = _q(14.5, 14.5)
    g = QLinearGradient(q(0, b, 0), q(0, b, h))
    g.setColorAt(0, QColor("#4caf50"))
    g.setColorAt(1, QColor("#ffd54f"))
    _poli(p, [q(0, b, 0), q(a, b, 0), q(a - d, b - d, h), q(d, b - d, h)], QBrush(g), GRIS_OSCURO)
    _poli(p, [q(a, 0, 0), q(a, b, 0), q(a - d, b - d, h), q(a - d, d, h)], QColor("#e53935"), GRIS_OSCURO)
    _poli(p, _cuadro(q, d, d, a - d, b - d, h), QColor("#81c784"), GRIS_OSCURO)
    _flecha(p, 4, 14, 4, 2.5, GRIS_OSCURO, 1.8, 4.2)


def _mapa_curvatura(p):
    g = QLinearGradient(QPointF(4, 24), QPointF(28, 8))
    for t, color in ((0, "#2b4fd8"), (0.3, "#22b8d6"), (0.5, "#43c443"), (0.72, "#f4d03f"), (1, "#e2382c")):
        g.setColorAt(t, QColor(color))
    camino = _onda(QPointF(3, 20), QPointF(19, 28), 4)
    camino.lineTo(29, 13)
    camino.connectPath(_onda(QPointF(13, 5), QPointF(29, 13), 4).toReversed())
    camino.closeSubpath()
    p.setPen(QPen(GRIS_OSCURO, 1.0))
    p.setBrush(QBrush(g))
    p.drawPath(camino)


def _isocurva(p):
    def f(u, v):
        return QPointF(4 + 22 * u + 3 * math.sin(math.pi * v), 8 + 16 * v - 5 * math.sin(math.pi * u) + 4 * v * u)
    borde = [f(u / 12, 0) for u in range(13)] + [f(1, v / 12) for v in range(13)]
    borde += [f(1 - u / 12, 1) for u in range(13)] + [f(0, 1 - v / 12) for v in range(13)]
    _poli(p, borde, SUP[0], BORDE_SUP)
    for k in (0.25, 0.5, 0.75):
        p.setPen(QPen(AZUL_LADO, 1.1))
        p.drawPolyline(QPolygonF([f(k, v / 12) for v in range(13)]))
        p.setPen(QPen(ROJO, 1.1))
        p.drawPolyline(QPolygonF([f(u / 12, k) for u in range(13)]))


def _accesibilidad(p):
    perfil = [(5, 12), (27, 12), (27, 16), (19, 16), (19, 25), (29, 25), (29, 29), (3, 29), (3, 25), (13, 25),
              (13, 16), (5, 16)]
    _poli(p, [QPointF(x, y) for x, y in perfil], GRISES[0], BORDE_GRIS)
    for color, tramos in ((QColor("#2e9e46"), [((5, 12), (27, 12)), ((19, 25), (27, 25)), ((27, 25), (29, 25)),
                                               ((3, 25), (5, 25))]),
                          (QColor("#d93b30"), [((5, 16), (13, 16)), ((19, 16), (27, 16)), ((5, 25), (13, 25)),
                                               ((13, 16), (13, 25)), ((19, 16), (19, 25))])):
        p.setPen(QPen(color, 2.4, Qt.SolidLine, Qt.FlatCap))
        for (x0, y0), (x1, y1) in tramos:
            p.drawLine(QPointF(x0, y0), QPointF(x1, y1))
    _flecha(p, 16, 1.5, 16, 9.5, GRIS_OSCURO, 1.8, 4.2)


def _radio_minimo(p):
    c = QPainterPath(QPointF(4, 29))
    c.quadTo(16, -12, 28, 29)
    _trazo(p, GRIS_OSCURO, 1.8)
    p.drawPath(c)
    p.setPen(QPen(ROJO, 1.4))
    p.drawEllipse(QPointF(16, 11.6), 3.6, 3.6)
    p.drawLine(QPointF(16, 11.6), QPointF(16, 8))
    _ptos(p, [(16, 11.6)], 2.0, ROJO)
    _letras(p, QRectF(18, 13, 12, 12), "R", ROJO, 11)


def _seccion(p):
    a, b, h = 18, 14, 12
    q = _q(*_centro(a, b, h))
    _guion(p, GRIS_OSCURO, 1.0)
    p.drawPolyline(QPolygonF([q(9, 0, h), q(a, 0, h), q(a, 0, 0), q(a, b, 0), q(9, b, 0)]))
    p.drawLine(q(a, b, 0), q(a, b, h))
    p.drawPolyline(QPolygonF([q(a, 0, h), q(a, b, h), q(9, b, h)]))
    _caja_en(p, q, 0, 0, 0, 9, b, h)
    cara = [q(9, 0, 0), q(9, b, 0), q(9, b, h), q(9, 0, h)]
    _poli(p, cara, QColor("#f7c9c4"), QColor("#a72c22"))
    p.save()
    p.setClipPath(_camino(cara))
    p.setPen(QPen(QColor("#c9372c"), 1.0))
    for k in range(-30, 40, 3):
        p.drawLine(QPointF(k, 32), QPointF(k + 32, 0))
    p.restore()


def _centro_masa(p):
    q = _caja_c(p, 14, 14, 13, (QColor(159, 207, 245, 120), QColor(74, 155, 224, 110), QColor(43, 120, 194, 110)))
    c = q(7, 7, 6.5)
    r = 5.5
    rect = QRectF(c.x() - r, c.y() - r, 2 * r, 2 * r)
    p.setPen(QPen(QColor("#111111"), 1.1))
    p.setBrush(QColor("#ffffff"))
    p.drawEllipse(rect)
    p.setPen(Qt.NoPen)
    p.setBrush(QColor("#111111"))
    p.drawPie(rect, 0, 90 * 16)
    p.drawPie(rect, 180 * 16, 90 * 16)


def _colores_componente(p):
    q = _q(16, 9)
    tonos = {(0, 0): "#e74c3c", (10, 0): "#2fa84f", (0, 10): "#f1c40f", (10, 10): "#4a9be0"}
    for (x, y), color in sorted(tonos.items(), key=lambda kv: kv[0][0] + kv[0][1]):
        base = QColor(color)
        _caja_en(p, q, x, y, 0, 8, 8, 8, (base.lighter(150), base, base.darker(130)), base.darker(190))


# ================================================================ INSERTAR
def _calcomania(p):
    a, b, h = 14, 14, 12
    q = _caja_c(p, a, b, h)
    p.save()
    _a_plano(p, q(0, b, h), q(a, b, h), q(0, b, 0), 10)
    p.setPen(QPen(QColor("#666666"), 0.5))
    p.setBrush(QColor("#ffffff"))
    p.drawRect(QRectF(1, 1, 8, 8))
    p.setPen(Qt.NoPen)
    p.setBrush(QColor("#9fd3ff"))
    p.drawRect(QRectF(1.6, 1.6, 6.8, 6.8))
    p.setBrush(QColor("#4caf50"))
    p.drawPolygon(QPolygonF([QPointF(1.6, 8.4), QPointF(4, 4.5), QPointF(6, 6.5), QPointF(7, 5.5),
                             QPointF(8.4, 8.4)]))
    p.setBrush(QColor("#ffd54f"))
    p.drawEllipse(QPointF(6.6, 3.2), 0.9, 0.9)
    p.restore()


def _insertar_archivo(p, sigla, color, glifo):
    _hoja(p, 6, 2.5, 26, 29.5, 5)
    glifo(p)
    p.setPen(Qt.NoPen)
    p.setBrush(color)
    p.drawRect(QRectF(3, 19, 21, 9))
    _letras(p, QRectF(3, 19, 21, 9), sigla, QColor("#ffffff"), 8)


def _glifo_svg(p):
    c = QPainterPath(QPointF(9, 15))
    c.cubicTo(11, 5, 19, 17, 22, 7)
    _trazo(p, GRIS_OSCURO, 1.5)
    p.drawPath(c)
    _ptos(p, [(9, 15), (22, 7)], 2.4)


def _glifo_dxf(p):
    _trazo(p, GRIS_OSCURO, 1.3)
    p.drawRect(QRectF(9, 7, 9, 8))
    p.drawEllipse(QPointF(20, 11), 3, 3)


def _insertar_malla(p):
    _esfera_malla(p, 18, 18, 10)
    _flecha(p, 3, 3, 10, 10.5, AZUL_LADO, 2.4)


def _insertar_componente(p):
    _caja(p, 12, 12, 11, 18, 16, 1.0, BLANCOS, GRIS_OSCURO)
    _flecha(p, 3, 3, 10, 10.5, AZUL_LADO, 2.4)


def _fijacion(p):
    p.setPen(QPen(BORDE_METAL, 0.9))
    p.setBrush(METAL[1])
    p.drawRect(QRectF(13, 12, 6, 17))                                   # caña
    p.save()
    p.setClipRect(QRectF(13, 12, 6, 17))
    p.setPen(QPen(BORDE_METAL, 0.9))
    for y in range(14, 31, 2):
        p.drawLine(QPointF(13, y + 1), QPointF(19, y - 1))
    p.restore()
    tapa = _regular(16, 7, 8, 6, 0)
    tapa = [QPointF(v.x(), 7 + (v.y() - 7) * 0.55) for v in tapa]
    lado = [tapa[0], tapa[1], tapa[2], tapa[3], tapa[3] + QPointF(0, 4), tapa[2] + QPointF(0, 4),
            tapa[1] + QPointF(0, 4), tapa[0] + QPointF(0, 4)]
    _poli(p, lado, METAL[2], BORDE_METAL)
    for k in (1, 2):
        p.drawLine(tapa[k], tapa[k] + QPointF(0, 4))
    _poli(p, tapa, METAL[0], BORDE_METAL)


# ================================================================ ENSAMBLAR
def _nuevo_componente(p):
    _caja(p, 12, 12, 12, 14, 14, 1.0, BLANCOS, GRIS_OSCURO)
    _mas(p, 25, 25, 5)


def _union(p):
    qa = _q(10, 18)
    _caja_en(p, qa, 0, 0, 0, 10, 10, 6, BLANCOS, GRIS_OSCURO)
    _caja(p, 7, 7, 7, 23, 9, 1.0, GRIS_COMP, GRIS_OSCURO)
    c = qa(5, 5, 6)
    arco = QPainterPath(QPointF(20, 18.5))
    arco.quadTo(19, 24, c.x() + 5.5, c.y() + 1)
    _guiones(p, GRIS_OSCURO, 1.3)
    p.drawPath(arco)
    _glifo_union(p, c.x(), c.y(), 4)


def _union_construida(p):
    q = _q(15.5, 13)
    _caja_en(p, q, 0, 0, 0, 14, 12, 5, BLANCOS, GRIS_OSCURO)
    _caja_en(p, q, 3, 2, 5, 8, 8, 8, GRIS_COMP, GRIS_OSCURO)
    c = q(11, 10, 5)
    _glifo_union(p, c.x(), c.y(), 3.8)


def _origen_union(p):
    q = _caja_c(p, 16, 16, 7, BLANCOS, GRIS_OSCURO)
    c = q(8, 8, 7)
    _flecha(p, c.x(), c.y(), c.x() + 9, c.y() + 5.2, ROJO, 1.6, 3.6)
    _flecha(p, c.x(), c.y(), c.x() - 9, c.y() + 5.2, VERDE, 1.6, 3.6)
    _flecha(p, c.x(), c.y(), c.x(), c.y() - 11, AZUL_LADO, 1.6, 3.6)
    _glifo_union(p, c.x(), c.y(), 4.4)


def _grupo_rigido(p):
    _caja(p, 8, 8, 8, 9.5, 12, 1.0, BLANCOS, GRIS_OSCURO)
    _caja(p, 8, 8, 8, 22.5, 12, 1.0, GRIS_COMP, GRIS_OSCURO)
    p.save()
    p.translate(16, 25)
    p.rotate(-18)
    p.setPen(QPen(GRIS_OSCURO, 2.2))
    p.setBrush(Qt.NoBrush)
    p.drawRoundedRect(QRectF(-10, -3, 11, 6), 3, 3)
    p.drawRoundedRect(QRectF(-1, -3, 11, 6), 3, 3)
    p.restore()


def _accionar_uniones(p):
    _caja(p, 10, 10, 6, 16, 16, 1.0, BLANCOS, GRIS_OSCURO)
    _glifo_union(p, 16, 16, 4.2)
    _arco_con_punta(p, 16, 16, 11, 200, 480, VERDE, 2.2, 4.8)


def _vinculo_movimiento(p):
    (x1, y1, r1), (x2, y2, r2) = ruedas = ((10, 20, 6.5), (23, 11, 5))
    n = QPointF(y2 - y1, x1 - x2) / math.hypot(x2 - x1, y2 - y1)          # normal a la línea de centros
    p.setPen(QPen(AZUL_LADO, 1.6))                                       # la correa que las vincula
    for signo in (1, -1):
        p.drawLine(QPointF(x1, y1) + n * (r1 * signo), QPointF(x2, y2) + n * (r2 * signo))
    for cx, cy, r in ruedas:
        p.setPen(QPen(GRIS_OSCURO, 1.2))
        p.setBrush(QColor("#ffffff"))
        p.drawEllipse(QPointF(cx, cy), r, r)
        _ptos(p, [(cx, cy)], 2.2)
    _arco_con_punta(p, x1, y1, 8.5, 150, 215, VERDE, 1.6, 3.8)
    _arco_con_punta(p, x2, y2, 7.5, 20, 80, VERDE, 1.6, 3.8)


def _conjunto_contacto(p):
    _caja(p, 9, 9, 9, 10, 13, 1.0, BLANCOS, GRIS_OSCURO)
    _caja(p, 9, 9, 9, 17.8, 17.5, 1.0, GRIS_COMP, GRIS_OSCURO)
    p.setPen(QPen(ROJO, 1.5, Qt.SolidLine, Qt.RoundCap))
    for dx, dy in ((-4, 0), (4, 0), (0, -4), (0, 4), (-2.8, -2.8), (2.8, 2.8), (2.8, -2.8), (-2.8, 2.8)):
        p.drawLine(QPointF(13.9 + dx * 0.35, 10.7 + dy * 0.35), QPointF(13.9 + dx, 10.7 + dy))


def _estudio_movimiento(p):
    _trazo(p, GRIS_OSCURO, 1.4)
    p.drawPolyline(QPolygonF([QPointF(4, 4), QPointF(4, 27), QPointF(28, 27)]))
    curva = QPolygonF([QPointF(4 + x, 16 - 8 * math.sin(x / 22 * 2 * math.pi)) for x in range(0, 23)])
    p.setPen(QPen(AZUL_LADO, 1.8))
    p.drawPolyline(curva)
    p.setPen(Qt.NoPen)
    p.setBrush(VERDE)
    p.drawPolygon(QPolygonF([QPointF(20, 18), QPointF(29, 23), QPointF(20, 28)]))


def _fijar_componente(p):
    _caja(p, 13, 13, 9, 15, 17, 1.0, BLANCOS, GRIS_OSCURO)
    p.setPen(QPen(GRIS_OSCURO, 1.6, Qt.SolidLine, Qt.RoundCap))
    p.drawLine(QPointF(15, 17.5), QPointF(20, 10))
    p.setPen(QPen(QColor("#8e1f17"), 0.9))
    p.setBrush(ROJO)
    p.drawEllipse(QPointF(22, 7), 5, 4)
    p.setBrush(QColor(255, 255, 255, 170))
    p.setPen(Qt.NoPen)
    p.drawEllipse(QPointF(20.5, 5.5), 1.5, 1.1)


# ================================================================ SELECCIONAR
def _seleccion_ventana(p):
    _guiones(p, AZUL_LADO, 1.4)
    p.setBrush(QColor(74, 155, 224, 60))
    p.drawRect(QRectF(3, 4, 20, 16))
    _cursor(p, 22, 19)


def _seleccion_libre(p):
    lazo = _curva_por([(13, 4), (25, 6), (24, 15), (15, 19), (5, 17), (4, 8), (13, 4)])
    _guiones(p, AZUL_LADO, 1.4)
    p.setBrush(QColor(74, 155, 224, 60))
    p.drawPath(lazo)
    _cursor(p, 18, 18)


def _seleccion_pintura(p):
    trazo = _curva_por([(4, 10), (10, 6), (14, 13), (20, 9), (24, 15)])
    p.setPen(QPen(QColor(74, 155, 224, 110), 7, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin))
    p.setBrush(Qt.NoBrush)
    p.drawPath(trazo)
    p.setPen(QPen(AZUL_LADO, 1.2))
    p.drawEllipse(QPointF(24, 15), 4, 4)
    _cursor(p, 24, 15)


def _filtro_seleccion(p):
    _poli(p, [QPointF(4, 5), QPointF(28, 5), QPointF(18.5, 16), QPointF(18.5, 26), QPointF(13.5, 29),
              QPointF(13.5, 16)], QColor("#d9dde2"), GRIS_OSCURO, 1.3)
    p.setPen(Qt.NoPen)
    p.setBrush(AZUL_FRENTE)
    p.drawPolygon(QPolygonF([QPointF(7, 7), QPointF(25, 7), QPointF(21, 11.5), QPointF(11, 11.5)]))


# ================================================================ SUPERFICIE
def _sup_extruir(p):
    base, arriba = QPointF(4, 25), QPointF(23, 20)
    _lamina(p, base + QPointF(0, -13), arriba + QPointF(0, -13), arriba, base, 3)
    _trazo(p, GRIS_OSCURO, 1.6)
    p.drawPath(_onda(base, arriba, 3))
    _flecha(p, 27.5, 24, 27.5, 5)


def _sup_revolucion(p):
    _eje(p, 16, 1.5, 16, 30.5, GRIS_OSCURO)
    lado = QPainterPath(QPointF(5, 9))
    lado.cubicTo(5, 20, 10, 25, 16, 25)
    lado.cubicTo(22, 25, 27, 20, 27, 9)
    lado.arcTo(QRectF(5, 5.5, 22, 7), 0, -180)
    g = QLinearGradient(QPointF(5, 0), QPointF(27, 0))
    g.setColorAt(0, SUP[2])
    g.setColorAt(0.4, SUP[0])
    g.setColorAt(1, SUP[2])
    p.setPen(QPen(BORDE_SUP, 1.0))
    p.setBrush(QBrush(g))
    p.drawPath(lado)
    p.setBrush(QColor("#fdf1de"))
    p.drawEllipse(QRectF(5, 5.5, 22, 7))
    _arco_con_punta(p, 16, 9, 9, 210, 330, GRIS_OSCURO, 1.3, 3.2)


def _sup_barrido(p):
    c = QPainterPath(QPointF(5, 27))
    c.cubicTo(5, 13, 13, 8, 27.5, 8)
    _guion(p, GRIS_OSCURO, 1.1)
    p.drawPath(c)                                                   # trayectoria
    cinta = QPolygonF(_muestras(c, 0.3, 1.0))
    for color, ancho in ((BORDE_SUP, 8.4), (SUP[1], 6.6), (SUP[0], 2.0)):
        p.setPen(QPen(color, ancho, Qt.SolidLine, Qt.FlatCap, Qt.RoundJoin))
        p.drawPolyline(cinta)
    _trazo(p, AZUL_BORDE, 2.0)
    p.drawLine(QPointF(2, 27), QPointF(8, 27))                      # perfil (una curva abierta)
    _ptos(p, [(2, 27), (8, 27)], 2.4)


def _sup_solevacion(p):
    a0, a1 = QPointF(7, 7), QPointF(25, 7)
    b0, b1 = QPointF(3, 25), QPointF(29, 25)
    _lamina(p, a0, a1, b1, b0, 0.1)
    arriba = QPainterPath(a0)
    arriba.quadTo(16, 1, 25, 7)
    abajo = _onda(b0, b1, 5)
    _trazo(p, GRIS_OSCURO, 0.8)
    for t in (0.25, 0.5, 0.75):
        p.drawLine(arriba.pointAtPercent(t), abajo.pointAtPercent(t))
    _trazo(p, AZUL_BORDE, 2.0)
    p.drawPath(arriba)
    p.drawPath(abajo)


def _parche(p):
    borde = _curva_por([(5, 16), (12, 7), (24, 8), (28, 18), (19, 26), (8, 24), (5, 16)])
    g = QRadialGradient(QPointF(15, 14), 15)
    g.setColorAt(0, QColor("#fff6e8"))
    g.setColorAt(1, SUP[2])
    p.setPen(Qt.NoPen)
    p.setBrush(QBrush(g))
    p.drawPath(borde)
    _trazo(p, AZUL_BORDE, 2.0)
    p.drawPath(borde)


def _reglada(p):
    arista = QPainterPath(QPointF(4, 9))
    arista.cubicTo(11, 3, 20, 13, 27, 6)
    corrida = QPointF(2, 16)
    _lamina(p, QPointF(4, 9), QPointF(27, 6), QPointF(27, 6) + corrida, QPointF(4, 9) + corrida, 0.1)
    _trazo(p, BORDE_SUP, 0.9)
    for t in (0.2, 0.4, 0.6, 0.8):
        a = arista.pointAtPercent(t)
        p.drawLine(a, a + corrida)
    _trazo(p, AZUL_BORDE, 2.2)
    p.drawPath(arista)


def _sup_desfase(p):
    _lamina(p, QPointF(3, 23), QPointF(19, 29), QPointF(29, 22), QPointF(13, 16), 2.5, SUP[2])
    _lamina(p, QPointF(3, 12), QPointF(19, 18), QPointF(29, 11), QPointF(13, 5), 2.5)
    for x, y in ((9, 15.5), (22, 15.5)):
        _flecha(p, x, y, x, y + 6, GRIS_OSCURO, 1.2, 3.2)


def _recortar_sup(p):
    a, b, c, d = QPointF(3, 20), QPointF(13, 6), QPointF(29, 12), QPointF(19, 26)
    corte = QPainterPath(QPointF(8, 10))
    corte.quadTo(18, 22, 24.5, 19)
    hoja = _camino([a, b, c, d])
    quita = QPainterPath(QPointF(8, 10))
    quita.quadTo(18, 22, 24.5, 19)
    quita.lineTo(29, 12)
    quita.lineTo(13, 6)
    quita.closeSubpath()
    queda = hoja.subtracted(quita)
    _guiones(p, BORDE_SUP, 1.0)
    p.drawPath(hoja.intersected(quita))
    p.setPen(QPen(BORDE_SUP, 1.0))
    p.setBrush(SUP[1])
    p.drawPath(queda)
    _trazo(p, AZUL_BORDE, 1.8)
    p.drawPath(corte)


def _destrimar(p):
    _lamina(p, QPointF(3, 20), QPointF(13, 6), QPointF(29, 12), QPointF(19, 26), 0.1)
    _guiones(p, BORDE_SUP, 1.2)
    p.setBrush(QColor("#fff3e2"))
    p.drawEllipse(QPointF(16, 16), 6.5, 4.5)
    for dx, dy in ((-1, 0), (1, 0), (0, -1), (0, 1)):
        _flecha(p, 16 + dx * 1.5, 16 + dy * 1, 16 + dx * 5.2, 16 + dy * 3.4, VERDE, 1.3, 2.8)


def _extender_sup(p):
    _lamina(p, QPointF(3, 18), QPointF(12, 6), QPointF(20, 10), QPointF(11, 22), 0.1)
    _guiones(p, BORDE_SUP, 1.1)
    p.setBrush(QColor(242, 189, 120, 90))
    p.drawPolygon(QPolygonF([QPointF(20, 10), QPointF(28, 14), QPointF(19, 26), QPointF(11, 22)]))
    _flecha(p, 16, 16.5, 25, 21, GRIS_OSCURO, 1.6, 4)


def _coser(p):
    _lamina(p, QPointF(3, 21), QPointF(11, 8), QPointF(18, 12), QPointF(10, 25), 0.1)
    _lamina(p, QPointF(18, 12), QPointF(26, 6), QPointF(29, 17), QPointF(10, 25), 0.1, SUP[2])
    p.setPen(QPen(VERDE, 1.6, Qt.SolidLine, Qt.RoundCap))
    for t in (0.18, 0.42, 0.66, 0.9):
        x, y = 18 + (10 - 18) * t, 12 + (25 - 12) * t
        p.drawLine(QPointF(x - 2.6, y - 1.2), QPointF(x + 2.6, y + 1.2))


def _descoser(p):
    q = _q(16, 16)
    s, d = 12, 2.2
    for caras, desp, color in (
            ([q(0, s, s), q(s, s, s), q(s, s, 0), q(0, s, 0)], QPointF(-d, d * 0.6), SUP[1]),
            ([q(s, s, s), q(s, 0, s), q(s, 0, 0), q(s, s, 0)], QPointF(d, d * 0.6), SUP[2]),
            ([q(0, 0, s), q(s, 0, s), q(s, s, s), q(0, s, s)], QPointF(0, -d * 1.2), SUP[0])):
        _poli(p, [c + desp for c in caras], color, BORDE_SUP, 1.0)


def _invertir_normal(p):
    _lamina(p, QPointF(3, 17), QPointF(16, 10), QPointF(29, 17), QPointF(16, 24), 0.1)
    _guion(p, GRIS_OSCURO, 1.2)
    p.drawLine(QPointF(16, 17), QPointF(16, 4))
    _flecha(p, 16, 17, 16, 29.5, AZUL_LADO, 2.0, 4.5)
    _arco_con_punta(p, 21, 11, 6, 120, -60, GRIS_OSCURO, 1.3, 3.4)


# ================================================================ MALLA
def _malla_teselar(p):
    _caja(p, 7, 7, 7, 8.5, 9.5)
    _caja_malla(p, _q(22.5, 16.5), 9, 9, 9)
    _flecha(p, 6, 21, 13, 26, GRIS_OSCURO, 1.8, 4.2)


def _reparar_malla(p):
    ext = _esfera_malla(p, 14, 15, 11)
    agujero = [ext[2], ext[3], QPointF(15.5, 15)]
    _poli(p, agujero, QColor("#ffffff"), ROJO, 1.2)
    p.save()
    p.translate(23, 23)
    p.rotate(45)
    p.setPen(QPen(GRIS_OSCURO, 0.9))
    p.setBrush(QColor("#9aa3ad"))
    p.drawRoundedRect(QRectF(-1.6, -2, 3.2, 9.5), 1.2, 1.2)
    llave = QPainterPath()
    llave.addEllipse(QPointF(0, -3.5), 3.6, 3.6)
    boca = QPainterPath()
    boca.addRect(QRectF(-1.3, -8, 2.6, 4.5))
    p.drawPath(llave.subtracted(boca))
    p.restore()


def _grupos_caras(p):
    a = b = h = 13
    q = _q(*_centro(a, b, h))
    _cara_malla(p, q(0, b, h), q(a, b, h), q(a, b, 0), q(0, b, 0), QColor("#f2a65a"), 2)
    _cara_malla(p, q(a, b, h), q(a, 0, h), q(a, 0, 0), q(a, b, 0), QColor("#a27fd6"), 2)
    _cara_malla(p, q(0, 0, h), q(a, 0, h), q(a, b, h), q(0, b, h), QColor("#8fd18f"), 2)


def _reducir_malla(p):
    q1, q2 = _q(9, 4), _q(23, 14.5)
    _cara_malla(p, *_cuadro(q1, 0, 0, 9, 9, 0), MALLA[1], 4)
    _cara_malla(p, *_cuadro(q2, 0, 0, 9, 9, 0), MALLA[1], 1)
    _flecha(p, 12, 19, 18, 23.5, GRIS_OSCURO, 1.8, 4.2)


def _remallar(p):
    p.setPen(QPen(BORDE_MALLA, 0.7))
    p.setBrush(MALLA[1])
    lado = 6.0
    alto = lado * 0.866
    for fila in range(3):
        for col in range(4):
            x0, y0 = 3.5 + col * lado + (fila % 2) * lado / 2, 7 + fila * alto
            p.drawPolygon(QPolygonF([QPointF(x0, y0 + alto), QPointF(x0 + lado / 2, y0),
                                     QPointF(x0 + lado, y0 + alto)]))
    _arco_con_punta(p, 16, 21, 7, 200, 340, GRIS_OSCURO, 1.6, 3.6)
    _arco_con_punta(p, 16, 21, 7, 20, 160, GRIS_OSCURO, 1.6, 3.6)


def _cortar_plano(p):
    q = _q(16, 16.5)
    _caja_malla(p, q, 12, 12, 7)
    _guiones(p, BORDE_MALLA, 1.0)
    p.drawPolygon(QPolygonF(_hexagono(_q(16, 16.5 - 7), 12, 12, 6)))
    _plano_q(p, _cuadro(q, -2.5, -2.5, 14.5, 14.5, 7))


def _vaciado_malla(p):
    a = b = 18
    h, e = 11, 2.5
    q = _q(*_centro(a, b, h))
    _caja_malla(p, q, a, b, h)
    _hueco(p, q, e, e, a - e, b - e, h, h - e, MALLA)


def _combinar_mallas(p):
    _caja_malla(p, _q(11, 11), 10, 10, 10)
    _caja_malla(p, _q(20, 16.5), 10, 10, 10, (MALLA[0].darker(108), MALLA[1].darker(108), MALLA[2].darker(108)))


def _suavizar_malla(p):
    picos = QPolygonF([QPointF(3 + 3.25 * k, 10 + (-3.5 if k % 2 else 3.5) * (0.4 + 0.6 * math.sin(k)))
                       for k in range(9)])
    p.setPen(QPen(BORDE_MALLA, 1.6, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin))
    p.setBrush(Qt.NoBrush)
    p.drawPolyline(picos)
    _flecha(p, 16, 15, 16, 20, GRIS_OSCURO, 1.6, 3.8)
    suave = _onda(QPointF(3, 25), QPointF(29, 25), 5)
    _trazo(p, AZUL_LADO, 2.0)
    p.drawPath(suave)


def _separar_malla(p):
    _caja_malla(p, _q(10, 12.5), 7, 10, 10)
    _caja_malla(p, _q(19.5, 16), 7, 10, 10)
    _flecha(p, 13, 26, 8, 28.5, GRIS_OSCURO, 1.4, 3.4)
    _flecha(p, 21, 5, 26, 2.5, GRIS_OSCURO, 1.4, 3.4)


def _escalar_malla(p):
    s, c = 12, 6
    q = _q(16, 16)
    _guion(p, BORDE_MALLA, 1.1)
    p.drawPolygon(QPolygonF(_hexagono(q, s, s, s)))
    for fin in (q(0, s, s), q(s, 0, s), q(s, s, 0)):
        p.drawLine(q(s, s, s), fin)
    o = q(0, s - c, 0)
    _caja_malla(p, _q(o.x(), o.y()), c, c, c, None, 1)
    _flecha(p, *_xy(q(c, s - c, c)), *_xy(q(s - 0.8, 0.8, s - 0.8)), GRIS_OSCURO, 1.8, 4.5)


def _convertir_malla(p):
    _caja_malla(p, _q(8.5, 9.5), 7, 7, 7, None, 1)
    _caja(p, 9, 9, 9, 22.5, 16.5)
    _flecha(p, 6, 21, 13, 26, GRIS_OSCURO, 1.8, 4.2)


def _borrar_rellenar(p):
    q = _q(16, 7)
    _cara_malla(p, *_cuadro(q, 0, 0, 16, 16, 0), MALLA[1], 4)
    c = q(8, 8, 0)
    p.setPen(Qt.NoPen)
    p.setBrush(QColor("#e9f7f5"))
    p.drawEllipse(c, 7, 4)
    _guiones(p, ROJO, 1.2)
    p.drawEllipse(c, 7, 4)


def _alinear_malla(p):
    p.setPen(QPen(BORDE_MALLA, 0.9))
    _cara_malla(p, QPointF(17, 7), QPointF(28, 7), QPointF(28, 27), QPointF(17, 27), MALLA[1], 3)
    _cara_malla(p, QPointF(4, 17), QPointF(13, 17), QPointF(13, 27), QPointF(4, 27), MALLA[0], 2)
    _guiones(p, BORDE_MALLA, 1.0)
    p.drawRect(QRectF(4, 7, 9, 10))
    _guiones(p, NARANJA, 1.4, (3, 2))
    p.drawLine(QPointF(2, 7), QPointF(30, 7))
    _flecha(p, 8.5, 16, 8.5, 9.5, GRIS_OSCURO, 1.6, 4)


def _exportar_malla(p):
    _caja_malla(p, _q(13, 14), 9, 9, 7)
    _flecha(p, 18, 13, 28, 3, NARANJA, 2.4)


# ================================================================ CHAPA
def _reglas_chapa(p):
    _hoja(p, 5, 3, 27, 29, 5)
    p.setPen(QPen(GRIS_OSCURO, 1.2))
    for y in (20, 24):
        p.drawLine(QPointF(9, y), QPointF(23, y))
    perfil = QPainterPath(QPointF(9, 15))
    perfil.lineTo(15, 15)
    perfil.quadTo(19, 15, 19, 11)
    perfil.lineTo(19, 7)
    for color, ancho in ((AZUL_BORDE, 3.4), (AZUL_FRENTE, 2.0)):
        p.setPen(QPen(color, ancho, Qt.SolidLine, Qt.FlatCap, Qt.RoundJoin))
        p.setBrush(Qt.NoBrush)
        p.drawPath(perfil)


def _pestana(p):
    q = _q(14, 14)
    _caja_en(p, q, 0, 0, 0, 14, 14, 2, GRISES, BORDE_GRIS)
    _caja_en(p, q, 14, 0, 0, 2, 14, 13)
    _mas(p, 6, 25, 4)


def _pestana_contorno(p):
    q = _q(15, 15.5)
    _caja_en(p, q, 0, 0, 12, 16, 6, 2)
    _caja_en(p, q, 0, 4, 2, 16, 2, 10)
    _caja_en(p, q, 0, 4, 0, 16, 10, 2)
    _guiones(p, GRIS_OSCURO, 1.0)
    p.drawPolyline(QPolygonF([q(16, 0, 14), q(16, 6, 14), q(16, 6, 2), q(16, 14, 2)]))


def _pestana_solevada(p):
    arriba = [QPointF(4, 9), QPointF(16, 3.5), QPointF(28, 9), QPointF(16, 14.5)]
    elipse = QRectF(11.5, 23, 9, 4.6)
    p.setPen(QPen(AZUL_BORDE, 0.9))
    p.setBrush(AZUL_LADO)
    p.drawPolygon(QPolygonF(arriba))
    lados = QPainterPath(arriba[0])
    lados.lineTo(arriba[3])
    lados.lineTo(arriba[2])
    lados.lineTo(20.5, 25.3)
    lados.arcTo(elipse, 0, -180)
    lados.closeSubpath()
    g = QLinearGradient(QPointF(4, 0), QPointF(28, 0))
    g.setColorAt(0, AZUL_ARRIBA)
    g.setColorAt(1, AZUL_FRENTE)
    p.setBrush(QBrush(g))
    p.drawPath(lados)
    p.setPen(QPen(AZUL_BORDE, 0.9))
    p.drawLine(arriba[3], QPointF(16, 27.6))


def _dobladillo(p):
    perfil = QPainterPath(QPointF(2, 25))
    perfil.lineTo(19, 25)
    perfil.arcTo(QRectF(15.5, 18, 7, 7), 270, 180)
    perfil.lineTo(8, 18)
    for desp, color in ((QPointF(5, -5), AZUL_LADO), (QPointF(0, 0), AZUL_FRENTE)):
        c = perfil.translated(desp)
        for col, ancho in ((AZUL_BORDE, 3.6), (color, 2.2)):
            p.setPen(QPen(col, ancho, Qt.SolidLine, Qt.FlatCap, Qt.RoundJoin))
            p.setBrush(Qt.NoBrush)
            p.drawPath(c)
    p.setPen(QPen(AZUL_BORDE, 0.9))
    for x, y in ((2, 25), (8, 18)):
        p.drawLine(QPointF(x, y), QPointF(x + 5, y - 5))


def _cierre_esquina(p):
    q = _q(16, 14.5)
    _caja_en(p, q, 0, 0, 0, 15, 15, 2)
    _caja_en(p, q, 0, 0, 2, 15, 2, 11)
    _caja_en(p, q, 0, 2, 2, 2, 13, 11)
    c = q(2, 2, 2)
    p.setPen(QPen(QColor("#163f66"), 0.9))
    p.setBrush(QColor("#163f66"))
    p.drawEllipse(QPointF(c.x(), c.y() + 0.5), 2.2, 1.3)
    p.setPen(QPen(NARANJA, 1.8))
    p.drawLine(q(2, 2, 3), q(2, 2, 13))


def _desgarro(p):
    a = b = h = 13
    q = _q(*_centro(a, b, h))
    g = QPointF(1.6, 0)
    _poli(p, [v - g for v in [q(0, b, 0), q(a, b, 0), q(a, b, h), q(0, b, h)]], AZUL_FRENTE)
    _poli(p, [v + g for v in [q(a, 0, 0), q(a, b, 0), q(a, b, h), q(a, 0, h)]], AZUL_LADO)
    _poli(p, [q(0, 0, h), q(a, 0, h), q(a, b, h) + g, q(a, b, h) - g, q(0, b, h)], AZUL_ARRIBA)
    p.setPen(QPen(ROJO, 1.4, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin))
    zig = [q(a, b, h) + QPointF(0.0 if k % 2 == 0 else (1.1 if k % 4 == 1 else -1.1), 0) + QPointF(0, k * 1.3)
           for k in range(int(h / 1.3) + 1)]
    p.drawPolyline(QPolygonF(zig))


def _bandas(p, camino, ancho=2.4, color=None):
    """Chapa vista de canto: banda azul con borde oscuro que sigue el camino."""
    for col, a in ((AZUL_BORDE, ancho + 1.6), (color or AZUL_FRENTE, ancho)):
        p.setPen(QPen(col, a, Qt.SolidLine, Qt.FlatCap, Qt.RoundJoin))
        p.setBrush(Qt.NoBrush)
        p.drawPath(camino)


def _unir_plegando(p):
    a = QPainterPath(QPointF(3, 25))
    a.lineTo(15, 25)
    b = QPainterPath(QPointF(24, 16))
    b.lineTo(24, 4)
    _bandas(p, a)
    _bandas(p, b)
    pliegue = QPainterPath(QPointF(15, 25))
    pliegue.arcTo(QRectF(6, 7, 18, 18), 270, 90)
    _bandas(p, pliegue, 2.4, QColor("#8fd18f"))


def _plegar_o_desplegar(p, plegar):
    fijo = QPainterPath(QPointF(3, 25))
    fijo.lineTo(14, 25)
    plano = QPainterPath(QPointF(14, 25))
    plano.lineTo(29, 25)
    doblado = QPainterPath(QPointF(14, 25))
    doblado.quadTo(17, 25, 17, 21)
    doblado.lineTo(17, 6)
    fantasma, real = (plano, doblado) if plegar else (doblado, plano)
    _guiones(p, AZUL_BORDE, 1.6)
    p.drawPath(fantasma)
    _bandas(p, fijo)
    _bandas(p, real)
    if plegar:
        _arco_con_punta(p, 15, 24, 12, 10, 70, GRIS_OSCURO, 1.6, 4)
    else:
        _arco_con_punta(p, 15, 24, 12, 70, 10, GRIS_OSCURO, 1.6, 4)


def _patron_plano(p):
    cruz = [(11, 3), (21, 3), (21, 11), (29, 11), (29, 21), (21, 21), (21, 29), (11, 29), (11, 21), (3, 21),
            (3, 11), (11, 11)]
    _poli(p, [QPointF(x, y) for x, y in cruz], AZUL_ARRIBA, AZUL_BORDE, 1.0)
    _guiones(p, AZUL_BORDE, 1.0)
    p.drawRect(QRectF(11, 11, 10, 10))


def _convertir_chapa(p):
    _caja(p, 7, 7, 7, 8, 9, 1.0, GRISES, BORDE_GRIS)
    _flecha(p, 7, 19, 13, 25, GRIS_OSCURO, 1.8, 4.2)
    q = _q(20, 16)
    _caja_en(p, q, 0, 0, 0, 9, 9, 1.8)
    _caja_en(p, q, 9, 0, 0, 1.8, 9, 9)


# ================================================================ ESPACIOS DE TRABAJO / VARIOS
def _dibujo(p):
    p.setPen(QPen(GRIS_OSCURO, 1.2))
    p.setBrush(QColor("#ffffff"))
    p.drawRect(QRectF(2.5, 5, 27, 22))
    p.setPen(QPen(GRIS_OSCURO, 0.8))
    p.setBrush(Qt.NoBrush)
    p.drawRect(QRectF(4.5, 7, 23, 18))
    p.drawRect(QRectF(19, 20, 8.5, 5))
    p.setPen(QPen(AZUL_LADO, 1.2))
    p.drawRect(QRectF(7, 13, 8, 8))
    p.drawRect(QRectF(7, 9, 8, 2.5))
    p.drawEllipse(QPointF(21.5, 13), 3.3, 3.3)


def _render(p):
    p.setPen(Qt.NoPen)
    p.setBrush(QColor(0, 0, 0, 45))
    p.drawEllipse(QPointF(16, 27.5), 12, 2.6)
    tetera = QPainterPath()
    tetera.addEllipse(QRectF(7, 11, 17, 15))
    pico = QPainterPath(QPointF(22, 20))
    pico.quadTo(26, 18, 28, 11)
    pico.lineTo(30, 10.5)
    pico.quadTo(28, 22, 22, 24)
    asa = QPainterPath()
    asa.addEllipse(QRectF(3, 14, 8, 9))
    asa_hueco = QPainterPath()
    asa_hueco.addEllipse(QRectF(5, 16, 4, 5))
    cuerpo = tetera.united(pico).united(asa.subtracted(asa_hueco))
    g = QRadialGradient(QPointF(12, 14), 15)
    g.setColorAt(0, QColor("#ffe3c2"))
    g.setColorAt(0.45, QColor("#e9934a"))
    g.setColorAt(1, QColor("#8a4513"))
    p.setPen(QPen(QColor("#5c2d0b"), 0.9))
    p.setBrush(QBrush(g))
    p.drawPath(cuerpo)
    p.drawEllipse(QRectF(10, 8.5, 11, 4))
    p.drawEllipse(QRectF(14, 5.5, 3, 3))
    p.setPen(Qt.NoPen)
    p.setBrush(QColor(255, 255, 255, 200))
    p.drawEllipse(QRectF(10.5, 14, 3, 4.5))


def _animacion(p):
    p.setPen(Qt.NoPen)
    p.setBrush(QColor("#3c3c3c"))
    p.drawRoundedRect(QRectF(2, 7, 28, 18), 1.5, 1.5)
    p.setBrush(QColor("#ffffff"))
    for x in range(4, 30, 4):
        p.drawRect(QRectF(x, 8.4, 2, 1.8))
        p.drawRect(QRectF(x, 21.8, 2, 1.8))
    for x0 in (4, 17):
        p.setBrush(QColor("#d9dde2"))
        p.drawRect(QRectF(x0, 11.5, 11, 9))
    _caja(p, 4, 4, 4, 8, 15, 1.0)
    _caja(p, 4, 4, 4, 24, 13.5, 1.0)


def _configuracion_tabla(p):
    p.setPen(QPen(GRIS, 1))
    p.setBrush(QColor("#ffffff"))
    p.drawRect(QRectF(3, 5, 26, 22))
    p.setPen(Qt.NoPen)
    p.setBrush(AZUL_FRENTE)
    p.drawRect(QRectF(3.5, 5.5, 25, 5))
    p.setBrush(AZUL_SEL)
    p.drawRect(QRectF(3.5, 16.2, 25, 5.3))
    p.setPen(QPen(GRIS, 1))
    for y in (10.5, 16, 21.5):
        p.drawLine(QPointF(3, y), QPointF(29, y))
    for x in (11, 20):
        p.drawLine(QPointF(x, 5), QPointF(x, 27))
    _caja(p, 3.6, 3.6, 3.6, 7, 16.2, 1.0)
    p.setPen(QPen(VERDE, 1.8, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin))
    p.drawPolyline(QPolygonF([QPointF(13, 18.8), QPointF(15, 20.5), QPointF(18.5, 17)]))


def _fx(p, x0):
    _letras(p, QRectF(x0, 8, 18, 22), "fx", GRIS_OSCURO, 14)


def _parametros_exportar(p):
    _fx(p, 1)
    _flecha(p, 18, 14, 28.5, 3.5, NARANJA, 2.4)


def _parametros_importar(p):
    _fx(p, 13)
    _flecha(p, 3, 3, 12, 12, AZUL_LADO, 2.4)


def _secuencias(p):
    p.setPen(QPen(GRIS, 1.4))
    p.drawLine(QPointF(8, 7), QPointF(8, 25))
    for k, y in enumerate((6.5, 16, 25.5)):
        p.setPen(Qt.NoPen)
        p.setBrush(AZUL_LADO)
        p.drawEllipse(QPointF(8, y), 4.6, 4.6)
        _letras(p, QRectF(3.4, y - 4.6, 9.2, 9.2), str(k + 1), QColor("#ffffff"), 7)
        p.setPen(QPen(GRIS_OSCURO, 1.6, Qt.SolidLine, Qt.RoundCap))
        p.drawLine(QPointF(15, y), QPointF(28 - 4 * (k % 2), y))


DIBUJOS_EXTRA = {
    # sólido / crear
    "barrido": _barrido, "solevacion": _solevacion, "nervio": _nervio, "red": _red, "labio": _labio,
    "repujado": _repujado, "saliente": _saliente, "encaje_presion": _encaje_presion, "agujero": _agujero,
    "rosca": _rosca, "bobina": _bobina, "tuberia": _tuberia, "patron_rectangular_3d": _patron_rectangular_3d,
    "patron_circular_3d": _patron_circular_3d, "patron_ruta": _patron_ruta, "simetria_3d": _simetria_3d,
    "engrosar": _engrosar, "relleno_contorno": _relleno_contorno, "cuerpo_envolvente": _cuerpo_envolvente,
    "operacion_base": _operacion_base, "derivar": _derivar, "crear_forma": _crear_forma,
    # modificar
    "pulsar_tirar": _pulsar_tirar, "empalme_3d": lambda p: _arista_viva(p, True),
    "chaflan_3d": lambda p: _arista_viva(p, False), "vaciado": _vaciado, "desmoldeo": _desmoldeo,
    "escala_3d": _escala_3d, "desfase_cara": _desfase_cara, "reemplazar_cara": _reemplazar_cara,
    "dividir_cara": _dividir_cara, "dividir_cuerpo": _dividir_cuerpo, "division_silueta": _division_silueta,
    "mover_copiar": _mover_copiar, "alinear": _alinear, "suprimir": _suprimir, "quitar": _quitar,
    "material_fisico": _material_fisico, "aspecto": _aspecto, "administrar_materiales": _administrar_materiales,
    "lista_materiales": _lista_materiales,
    # construir
    "scu": _scu, "plano_angulo": _plano_angulo, "plano_tangente": _plano_tangente, "plano_medio": _plano_medio,
    "plano_perpendicular": _plano_perpendicular, "plano_dos_aristas": _plano_dos_aristas,
    "plano_tres_puntos": _plano_tres_puntos, "plano_ruta": _plano_ruta, "eje_cilindro": _eje_cilindro,
    "eje_perpendicular": _eje_perpendicular, "eje_dos_planos": _eje_dos_planos, "eje_dos_puntos": _eje_dos_puntos,
    "eje_arista": _eje_arista, "punto_vertice": _punto_vertice, "punto_dos_aristas": _punto_dos_aristas,
    "punto_tres_planos": _punto_tres_planos, "punto_centro": _punto_centro,
    "punto_arista_plano": _punto_arista_plano, "punto_ruta": _punto_ruta,
    # inspeccionar
    "interferencia": _interferencia, "curvatura_peine": _curvatura_peine, "cebra": _cebra,
    "mapa_entorno": _mapa_entorno, "angulo_desmoldeo": _angulo_desmoldeo, "mapa_curvatura": _mapa_curvatura,
    "isocurva": _isocurva, "accesibilidad": _accesibilidad, "radio_minimo": _radio_minimo, "seccion": _seccion,
    "centro_masa": _centro_masa, "colores_componente": _colores_componente,
    # insertar
    "calcomania": _calcomania,
    "insertar_svg": lambda p: _insertar_archivo(p, "SVG", NARANJA, _glifo_svg),
    "insertar_dxf": lambda p: _insertar_archivo(p, "DXF", AZUL_LADO, _glifo_dxf),
    "insertar_malla": _insertar_malla, "insertar_componente": _insertar_componente, "fijacion": _fijacion,
    # ensamblar
    "nuevo_componente": _nuevo_componente, "union": _union, "union_construida": _union_construida,
    "origen_union": _origen_union, "grupo_rigido": _grupo_rigido, "accionar_uniones": _accionar_uniones,
    "vinculo_movimiento": _vinculo_movimiento, "conjunto_contacto": _conjunto_contacto,
    "estudio_movimiento": _estudio_movimiento, "fijar_componente": _fijar_componente,
    # seleccionar
    "seleccion_ventana": _seleccion_ventana, "seleccion_libre": _seleccion_libre,
    "seleccion_pintura": _seleccion_pintura, "filtro_seleccion": _filtro_seleccion,
    # superficie
    "sup_extruir": _sup_extruir, "sup_revolucion": _sup_revolucion, "sup_barrido": _sup_barrido,
    "sup_solevacion": _sup_solevacion, "parche": _parche, "reglada": _reglada, "sup_desfase": _sup_desfase,
    "recortar_sup": _recortar_sup, "destrimar": _destrimar, "extender_sup": _extender_sup, "coser": _coser,
    "descoser": _descoser, "invertir_normal": _invertir_normal,
    # malla
    "malla_teselar": _malla_teselar, "reparar_malla": _reparar_malla, "grupos_caras": _grupos_caras,
    "reducir_malla": _reducir_malla, "remallar": _remallar, "cortar_plano": _cortar_plano,
    "vaciado_malla": _vaciado_malla, "combinar_mallas": _combinar_mallas, "suavizar_malla": _suavizar_malla,
    "separar_malla": _separar_malla, "escalar_malla": _escalar_malla, "convertir_malla": _convertir_malla,
    "borrar_rellenar": _borrar_rellenar, "alinear_malla": _alinear_malla, "exportar_malla": _exportar_malla,
    # chapa
    "reglas_chapa": _reglas_chapa, "pestana": _pestana, "pestana_contorno": _pestana_contorno,
    "pestana_solevada": _pestana_solevada, "dobladillo": _dobladillo, "cierre_esquina": _cierre_esquina,
    "desgarro": _desgarro, "unir_plegando": _unir_plegando, "plegar": lambda p: _plegar_o_desplegar(p, True),
    "desplegar": lambda p: _plegar_o_desplegar(p, False), "patron_plano": _patron_plano,
    "convertir_chapa": _convertir_chapa,
    # espacios de trabajo / varios
    "dibujo": _dibujo, "render": _render, "animacion": _animacion, "configuracion_tabla": _configuracion_tabla,
    "parametros_exportar": _parametros_exportar, "parametros_importar": _parametros_importar,
    "secuencias": _secuencias,
}

# Los ayudantes de iconos.py se importan AL FINAL, a propósito: iconos.py importa este módulo en su última
# línea (DIBUJOS.update), así que cuando se carga cualquiera de los dos primero, DIBUJOS_EXTRA ya existe y
# los nombres que iconos.py define antes de esa línea también. Las funciones de arriba solo usan estos
# nombres al ejecutarse, nunca al cargarse el módulo.
from .iconos import (AZUL_ARRIBA, AZUL_BORDE, AZUL_FRENTE, AZUL_LADO, GRIS, GRIS_OSCURO, NARANJA, ROJO,  # noqa: E402
                     VERDE, _arco_con_punta, _caja, _cilindro, _curva_por, _flecha, _guion, _iso, _letras, _mas,
                     _poli, _ptos, _regular, _trazo)
