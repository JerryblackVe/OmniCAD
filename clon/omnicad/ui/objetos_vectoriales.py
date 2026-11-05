# -*- coding: utf-8 -*-
"""Manipulación de objetos en el editor existente: caché visual, matriz provisional y un único aceptar."""
import math

import numpy as np
from PySide6.QtCore import QEvent, QPointF, QRectF, Qt
from PySide6.QtGui import QColor, QPainterPath, QPainterPathStroker, QPen, QPolygonF, QTransform
from PySide6.QtWidgets import (QCheckBox, QComboBox, QFormLayout, QFrame, QHBoxLayout, QLabel, QLineEdit,
                              QMenu, QPushButton, QScrollArea, QToolButton, QVBoxLayout, QWidget)

from ..restricciones import ErrorBoceto
from ..restricciones import objetos as ob
from ..restricciones.boceto import Texto, puntos_primitiva
from ..timeline.parametros import ANGULO, ESCALAR, LONGITUD, ErrorExpresion, nombres_usados
from . import formato, temas
from .formulario import Seccion, armar_cabecera

ETIQUETAS = {"x": "Posición X (mm)", "y": "Posición Y (mm)", "ancho": "Ancho (mm)", "alto": "Alto (mm)",
             "angulo": "Ángulo (°)", "sx": "Escala X", "sy": "Escala Y", "px": "Pivote X (mm)", "py": "Pivote Y (mm)"}
ALINEACIONES = {"Izquierda": "izquierda", "Derecha": "derecha", "Arriba": "arriba", "Abajo": "abajo",
                "Centro horizontal": "centro_h", "Centro vertical": "centro_v", "Centrar en origen": "origen",
                "Distribuir horizontal": "distribuir_h", "Distribuir vertical": "distribuir_v"}


def _camino(polis):
    """Encadena muestras para que el interior y los agujeros tengan la misma regla par/impar."""
    extremos, usadas = {}, set()
    clave = lambda p: (round(p[0], 7), round(p[1], 7))  # noqa: E731
    for k, poli in enumerate(polis):
        if len(poli) >= 2:
            for q in (poli[0], poli[-1]):
                extremos.setdefault(clave(q), []).append(k)
    camino = QPainterPath()
    camino.setFillRule(Qt.OddEvenFill)
    for k, poli in enumerate(polis):
        if k in usadas or len(poli) < 2:
            continue
        usadas.add(k)
        cadena = list(poli)
        while clave(cadena[-1]) != clave(cadena[0]):
            otros = [j for j in extremos.get(clave(cadena[-1]), ()) if j not in usadas]
            if len(otros) != 1:
                break
            j = otros[0]
            siguiente = polis[j]
            if clave(siguiente[-1]) == clave(cadena[-1]):
                siguiente = siguiente[::-1]
            cadena.extend(siguiente[1:])
            usadas.add(j)
        camino.moveTo(*cadena[0])
        for q in cadena[1:]:
            camino.lineTo(*q)
        if clave(cadena[-1]) == clave(cadena[0]):
            camino.closeSubpath()
    return camino


class ControlObjetos:
    def __init__(self, lienzo):
        self.l = lienzo
        self.panel = None
        self.arrastre = None
        self.previa = None
        self.modo_perfiles = False
        self.snap = True
        self.guias = []
        self._cache = {}
        self._poligonos = {}
        self._firma = None
        self._cajas = {}
        self._sobre = None
        self.editar_pivote = False
        self._seleccion_objetos = []
        self.previa_pivote = None

    def seleccion(self):
        b = self.l.b
        indice = ob.indice(b)
        return list(dict.fromkeys(indice[i][0] if i in indice else i for i in self.l.seleccion
                                  if i in b.objetos or i in indice))

    def set_modo_perfiles(self, activo):
        """Los clics pertenecen a un solo modo; volver recupera los objetos elegidos."""
        self.cancelar()
        if activo:
            self._seleccion_objetos = self.seleccion()
        self.modo_perfiles = activo
        self.l.seleccion = [] if activo else [i for i in self._seleccion_objetos if i in self.l.b.objetos]
        self.l.perfiles_sel = []
        self.l._notificar_seleccion()
        self.l.update()

    def registrar_textos(self):
        """Texto libre nuevo o anterior: identidad lógica; sus parámetros y sus contornos siguen siendo texto."""
        b = self.l.b
        indice = ob.indice(b)
        for c in list(b.curvas.values()):
            if isinstance(c, Texto) and c.id not in indice:
                try:
                    oid = ob.crear(b, [c.id] + b._lineas_auxiliares(c), "Texto")
                    b.objetos[oid]["texto_automatico"] = c.id
                except ErrorBoceto:
                    continue  # un texto restringido a otra geometría conserva la interacción de restricciones

    def _datos(self):
        l, b = self.l, self.l.b
        firma = (l._generacion, l.width(), l.height(), l.escala, tuple(l.centro),
                 None if l._mvp is None else l._mvp.tobytes(), tuple(b.objetos), l._texto_oculto,
                 tuple(sorted(l.mostrar.items())))
        if firma != self._firma:
            self._firma, self._cache, self._cajas, self._poligonos = firma, {}, {}, {}
            visibles = ob.curvas_visibles(b)
            for oid in ob.raices(b):
                prims = [p for cid in ob.curvas(b, [oid]) for p in b.primitivas(cid)]
                # Contenido resuelto del texto, sin cambiar la receta del editor.
                if any(isinstance(b.curvas[i], Texto) for i in ob.curvas(b, [oid])):
                    reales = l.geometria_real()
                    ids = set(ob.curvas(b, [oid]))
                    prims = [p for p in reales if p[1] in ids]
                mundo = _camino([puntos_primitiva(p, 64) for p in prims if p[1] != l._texto_oculto
                                 and p[1] in visibles and l._visible(b.curvas[p[1]])])
                t = self._a_pantalla(np.eye(3))
                pantalla = t.map(mundo)
                borde = QPainterPathStroker()
                borde.setWidth(12)
                self._cache[oid] = (pantalla, borde.createStroke(pantalla))
                self._poligonos[oid] = pantalla.toSubpathPolygons()
                limites = np.asarray([ob.limites_primitiva(p) for p in prims])
                self._cajas[oid] = (float(limites[:, 0].min()), float(limites[:, 1].min()),
                                     float(limites[:, 2].max()), float(limites[:, 3].max())) if len(limites) else (0, 0, 0, 0)
        return self._cache

    def _a_pantalla(self, m):
        """Homografía del plano: también funciona mirando el boceto en perspectiva."""
        puntos = ((0, 0), (100, 0), (100, 100), (0, 100))
        destino = QPolygonF([self.l.a_px(*(m[:2, :2] @ p + m[:2, 2])) for p in puntos])
        t = QTransform()
        QTransform.quadToQuad(QPolygonF([QPointF(*p) for p in puntos]), destino, t)
        return t

    def _delta_pantalla(self, m):
        inversa, ok = self._a_pantalla(np.eye(3)).inverted()
        return inversa * self._a_pantalla(m) if ok else QTransform()

    def transformacion_texto(self):
        tid = (self.l._previa_texto or {}).get("existente")
        registro = ob.indice(self.l.b).get(tid)
        return self._delta_pantalla(registro[2]) if registro is not None else QTransform()

    def posicion_texto(self, pos):
        inversa, ok = self.transformacion_texto().inverted()
        return inversa.map(pos) if ok else pos

    def todos_en(self, pos):
        """Objetos raíz visibles bajo `pos`, del de arriba al de abajo (para elegir entre superpuestos)."""
        if self.modo_perfiles:
            return []
        b = self.l.b
        return [oid for oid, (camino, borde) in reversed(list(self._datos().items()))
                if b.objetos[oid]["visible"] and (camino.contains(pos) or borde.contains(pos)
                                                  or isinstance(b.curvas.get(b.objetos[oid].get("texto_automatico")), Texto)
                                                  and camino.boundingRect().contains(pos))]

    def en(self, pos):
        if self.modo_perfiles:
            return None
        for oid, (camino, borde) in reversed(list(self._datos().items())):
            o = self.l.b.objetos[oid]
            tid = o.get("texto_automatico")
            texto = self.l.b.curvas.get(tid)
            if o["visible"] and (camino.contains(pos) or borde.contains(pos) or
                                 isinstance(texto, Texto) and camino.boundingRect().contains(pos)):
                return tid if (isinstance(texto, Texto) and texto.camino in self.l.b.curvas
                               and np.array_equal(o["matriz"], ob.IDENTIDAD)) else oid
        return None

    def caja(self):
        self._datos()
        ids = self.seleccion()
        if not ids:
            return None
        cs = [self._cajas[i] if i in self._cajas else ob.caja(self.l.b, [i]) for i in ids]   # dentro de un grupo
        return (min(c[0] for c in cs), min(c[1] for c in cs), max(c[2] for c in cs), max(c[3] for c in cs))

    def pivote(self):
        ids = self.seleccion()
        if len(ids) == 1 and self.l.b.objetos[ids[0]]["pivote"] is not None:
            return ob.pivote(self.l.b, ids[0])
        x0, y0, x1, y1 = self.caja()
        return ((x0 + x1) / 2, (y0 + y1) / 2)

    def manijas(self):
        caja = self.caja()
        if caja is None or self.modo_perfiles or self.l.entrada is not None:
            return {}
        x0, y0, x1, y1 = caja
        xm, ym = (x0 + x1) / 2, (y0 + y1) / 2
        mm = [(x0, y0), (xm, y0), (x1, y0), (x1, ym), (x1, y1), (xm, y1), (x0, y1), (x0, ym)]
        def pantalla(p):
            if self.previa is not None:
                p = self.previa[:2, :2] @ p + self.previa[:2, 2]
            return self.l.a_px(*p)
        r = {f"escala{k}": pantalla(p) for k, p in enumerate(mm)}
        arriba = pantalla((xm, y1))
        r["rotar"] = arriba + QPointF(0, -28)
        pivote = self.arrastre.get("nuevo_pivote") if self.arrastre is not None else self.previa_pivote
        r["pivote"] = self.l.a_px(*pivote) if pivote is not None else pantalla(self.pivote())
        return r

    def manija_en(self, pos):
        for tipo, q in self.manijas().items():
            if tipo == "pivote" and not self.editar_pivote:
                continue  # el centro agarra el objeto; el pivote se edita explícitamente desde el panel
            if (pos - q).manhattanLength() <= 10:
                return tipo
        return None

    def presionar(self, pos):
        tipo = self.manija_en(pos)
        if tipo:
            self.iniciar(tipo, pos)
            return True
        return False

    def iniciar(self, tipo, pos):
        if not self.seleccion():
            return
        if any(self.l.b.objetos[i]["bloqueado"] for i in self.seleccion()):
            self.l.mensaje.emit("Desbloqueá el objeto antes de transformarlo.")
            return
        self.arrastre = {"tipo": tipo, "inicio": self.l.a_mm(pos), "pos": pos, "caja": self.caja(),
                         "pivote": self.pivote(), "m": np.eye(3), "movio": False}
        self.previa = None
        self.guias = []
        self.l.mensaje.emit("Arrastrá · Mayús: eje/proporción/15° · Alt: centro · Ctrl: sin imanes · Esc: cancelar")

    def _snap(self, delta, mods):
        self.guias = []
        if not self.snap or mods & Qt.ControlModifier:
            return delta
        tol = 7 / self.l.px_por_mm()
        x0, y0, x1, y1 = self.arrastre["caja"]
        propios = ((x0, y0), ((x0 + x1) / 2, (y0 + y1) / 2), (x1, y1))
        metas = [(0.0, 0.0)]
        for oid, c in self._cajas.items():
            if oid not in self.seleccion() and self.l.b.objetos[oid]["visible"]:
                a, bb, c1, d = c
                metas.extend(((a, bb), (c1, d), ((a + c1) / 2, (bb + d) / 2)))
        # Los extremos del boceto tradicional siguen sirviendo de referencia, sin dibujarlos todos.
        internos = {p for cid in ob.indice(self.l.b) for p in self.l.b.curvas[cid].puntos()}
        metas.extend((p.x, p.y) for p in self.l.b.puntos.values() if p.id not in internos and not p.proyectado)
        salida = list(delta)
        for eje in (0, 1):
            candidatos = [(abs(t[eje] - (p[eje] + delta[eje])), t[eje] - p[eje], t[eje])
                          for p in propios for t in metas]
            if self.l.ajustar_grilla:
                paso = self.l.paso_grilla()
                candidatos.extend((abs(round((p[eje] + delta[eje]) / paso) * paso - p[eje] - delta[eje]),
                                    round((p[eje] + delta[eje]) / paso) * paso - p[eje],
                                    round((p[eje] + delta[eje]) / paso) * paso) for p in propios)
            distancia, valor, guia = min(candidatos)
            if distancia <= tol:
                salida[eje] = valor
                self.guias.append((eje, guia))
        return salida

    def mover(self, pos, mods):
        d = self.arrastre
        if d is None:
            return
        if not d["movio"]:
            if (pos - d["pos"]).manhattanLength() <= 3:
                return
            d["movio"] = True
            if self.l.visor is not None:
                self.l.visor.set_perfiles([])
        x, y = self.l.a_mm(pos)
        ix, iy = d["inicio"]
        tipo = d["tipo"]
        x0, y0, x1, y1 = d["caja"]
        if tipo == "mover":
            dx, dy = self._snap((x - ix, y - iy), mods)
            if mods & Qt.ShiftModifier:
                dx, dy = (dx, 0) if abs(dx) >= abs(dy) else (0, dy)
            m = ob.afin(dx, dy)
        elif tipo == "pivote":
            d["nuevo_pivote"] = (x, y)
            m = np.eye(3)
        elif tipo == "rotar":
            px, py = d["pivote"]
            a = math.degrees(math.atan2(y - py, x - px) - math.atan2(iy - py, ix - px))
            if mods & Qt.ShiftModifier:
                a = round(a / 15) * 15
            m = ob.afin(angulo=a, pivote=(px, py))
        else:
            k = int(tipo[-1])
            puntos = ((x0, y0), ((x0 + x1) / 2, y0), (x1, y0), (x1, (y0 + y1) / 2),
                      (x1, y1), ((x0 + x1) / 2, y1), (x0, y1), (x0, (y0 + y1) / 2))
            base = ((x0 + x1) / 2, (y0 + y1) / 2) if mods & Qt.AltModifier else puntos[(k + 4) % 8]
            if mods & Qt.ControlModifier and not mods & Qt.AltModifier:
                base = d["pivote"]
            q = puntos[k]
            sx = (x - base[0]) / (q[0] - base[0]) if abs(q[0] - base[0]) > 1e-9 else 1.0
            sy = (y - base[1]) / (q[1] - base[1]) if abs(q[1] - base[1]) > 1e-9 else 1.0
            mantener = all(self.l.b.objetos[i]["proporciones"] for i in self.seleccion())
            if k % 2:
                sx = 1.0 if k in (1, 5) else sx
                sy = 1.0 if k in (3, 7) else sy
            if mods & Qt.ShiftModifier:
                mantener = not mantener
            if mantener:
                sx = sy = sx if k in (3, 7) else sy if k in (1, 5) else max(sx, sy)
            m = ob.afin(sx=max(sx, 1e-6), sy=max(sy, 1e-6), pivote=base)
        d["m"] = m
        self.previa = m
        if self.panel is not None:
            self.panel.actualizar_medidas()
        self.l.update()

    def soltar(self):
        d, self.arrastre = self.arrastre, None
        self.previa, self.previa_pivote, self.guias = None, None, []
        if d is not None and d["movio"]:
            if d["tipo"] == "pivote":
                self.aplicar(lambda: [ob.poner_pivote(self.l.b, i, d["nuevo_pivote"]) for i in self.seleccion()])
            else:
                self.aplicar(lambda: ob.transformar(self.l.b, self.seleccion(), d["m"]))
        self.notificar()
        self.l.update()

    def cancelar(self):
        if self.arrastre is None and self.previa is None and self.previa_pivote is None:
            return False
        self.arrastre = self.previa = None
        self.previa_pivote = None
        self.guias = []
        self.l.cambio.emit()
        self.notificar()
        self.l.update()
        return True

    def aplicar(self, funcion):
        from ..api.herramientas_objetos_vectoriales import textos_resueltos
        def cambiar():
            with textos_resueltos(self.l.b, self.l.valores_parametros()):
                try:
                    funcion()
                except ValueError as e:
                    raise ErrorBoceto(str(e)) from e
        seleccion = list(self.l.seleccion)
        mensajes = []
        self.l.mensaje.connect(mensajes.append)
        try:
            ok = self.l.aplicar_cambio(cambiar, anclar=False)
        finally:
            self.l.mensaje.disconnect(mensajes.append)
        if not ok:
            self.l.seleccion = seleccion
            if self.panel is not None:
                self.panel.error.setText(mensajes[-1] if mensajes else "No se pudo aplicar el cambio.")
        self._firma = None
        self.notificar()
        self.l.update()
        return ok

    def estado(self):
        ids = self.seleccion()
        if not ids:
            return None
        caja = self.caja()
        m = ob.acumulada(self.l.b, ids[0]) if len(ids) == 1 else np.eye(3)
        p = self.pivote()
        if self.previa is not None:
            m = self.previa @ m
            x0, y0, x1, y1 = caja
            pts = np.array(((x0, y0), (x1, y0), (x1, y1), (x0, y1))) @ self.previa[:2, :2].T + self.previa[:2, 2]
            caja = (*pts.min(axis=0), *pts.max(axis=0))
            p = self.previa[:2, :2] @ p + self.previa[:2, 2]
        x0, y0, x1, y1 = caja
        return {"x": x0, "y": y0, "ancho": x1 - x0, "alto": y1 - y0,
                "angulo": math.degrees(math.atan2(m[1, 0], m[0, 0])),
                "sx": float(np.linalg.norm(m[:2, 0])), "sy": float(np.linalg.norm(m[:2, 1])), "px": p[0], "py": p[1]}

    def notificar(self):
        if self.panel is not None:
            self.panel.sincronizar()

    def matriz_campo(self, clave, valor):
        e, ids = self.estado(), self.seleccion()
        if e is None:
            raise ErrorBoceto("Elegí un objeto para transformar.")
        p = self.pivote()
        if clave in ("px", "py"):
            return None, (valor if clave == "px" else p[0], valor if clave == "py" else p[1])
        if clave in ("x", "y"):
            return ob.afin(valor - e["x"] if clave == "x" else 0, valor - e["y"] if clave == "y" else 0), None
        if clave == "angulo":
            return ob.afin(angulo=valor - e["angulo"], pivote=p), None
        if valor <= 0:
            raise ErrorBoceto("El tamaño y la escala deben ser positivos.")
        factor = valor / max(e[clave], 1e-12)
        sx, sy = (factor, 1.0) if clave in ("ancho", "sx") else (1.0, factor)
        if all(self.l.b.objetos[i]["proporciones"] for i in ids):
            sx = sy = factor
        if clave in ("sx", "sy") and len(ids) == 1:
            lineal = ob.acumulada(self.l.b, ids[0])[:2, :2]
            m = np.eye(3)
            m[:2, :2] = lineal @ np.diag((sx, sy)) @ np.linalg.inv(lineal)
            m[:2, 2] = p - m[:2, :2] @ p
            return m, None
        return ob.afin(sx=sx, sy=sy, pivote=p), None

    def confirmar_campo(self, clave, valor, expresion):
        """La medida escrita se confirma una vez; una referencia a parámetros conserva su fórmula."""
        e, ids = self.estado(), self.seleccion()
        m, p = self.matriz_campo(clave, valor)
        if p is not None:
            return self.aplicar(lambda: [ob.poner_pivote(self.l.b, i, p) for i in ids])
        parametros, pasos = None, None
        if nombres_usados(expresion) & self.l.valores_parametros().keys():
            pivote = list(self.pivote())
            if clave in ("x", "y", "angulo"):
                unidad = "deg" if clave == "angulo" else "mm"
                parametros = {"angulo" if clave == "angulo" else "dx" if clave == "x" else "dy":
                              f"({expresion}) - {e[clave]:.17g} {unidad}", "pivote": pivote}
            else:
                unidad = " mm" if clave in ("ancho", "alto") else ""
                factor = f"({expresion}) / ({e[clave]:.17g}{unidad})"
                proporcional = all(self.l.b.objetos[i]["proporciones"] for i in ids)
                parametros = {"sx": factor if proporcional or clave in ("ancho", "sx") else 1,
                              "sy": factor if proporcional or clave in ("alto", "sy") else 1, "pivote": pivote}
                if clave in ("sx", "sy") and len(ids) == 1 and not proporcional:
                    marco = np.eye(3)
                    marco[:2, :2] = ob.acumulada(self.l.b, ids[0])[:2, :2]
                    marco[:2, 2] = pivote
                    parametros["pivote"] = [0, 0]
                    pasos = [{"matriz": np.linalg.inv(marco).tolist()}, {"parametros": parametros},
                             {"matriz": marco.tolist()}]
                    parametros = None
        return self.aplicar(lambda: ob.transformar(self.l.b, ids, m, parametros, pasos=pasos))

    def dibujar(self, p):
        datos = self._datos()
        seleccion = self.seleccion()
        for oid, (camino, _borde) in datos.items():
            if not self.l.b.objetos[oid]["visible"]:
                continue
            color = QColor(0, 180, 255) if oid in seleccion else QColor(255, 170, 40) if oid == self._sobre else (
                QColor(90, 160, 255) if self.l._oscuro() else QColor(25, 90, 200))
            p.save()
            if self.previa is not None and oid in seleccion:
                p.setTransform(self._delta_pantalla(self.previa), True)
            pluma = QPen(color, 2.5 if oid in seleccion else 1.5)
            pluma.setCosmetic(True)
            p.setPen(pluma)
            p.setBrush(Qt.NoBrush)
            for poli in self._poligonos[oid]:
                p.drawPolyline(poli)
            p.restore()
        if not seleccion or self.l.herramienta != "seleccionar" or self.modo_perfiles or self.l.entrada is not None:
            return
        x0, y0, x1, y1 = self.caja()
        esq = [(x0, y0), (x1, y0), (x1, y1), (x0, y1)]
        if self.previa is not None:
            esq = [self.previa[:2, :2] @ q + self.previa[:2, 2] for q in esq]
        p.setPen(QPen(QColor(0, 150, 255), 1, Qt.DashLine))
        p.drawPolygon(QPolygonF([self.l.a_px(*q) for q in esq]))
        p.setPen(QPen(QColor(0, 150, 255), 1))
        manijas = self.manijas()
        if manijas:
            p.drawLine(manijas["escala5"], manijas["rotar"])
        for tipo, q in manijas.items():
            p.setBrush(QColor(temas.color("fondo")))
            if tipo in ("rotar", "pivote"):
                p.drawEllipse(q, 5, 5)
                if tipo == "pivote":
                    p.drawLine(q + QPointF(-8, 0), q + QPointF(8, 0))
                    p.drawLine(q + QPointF(0, -8), q + QPointF(0, 8))
            else:
                p.drawRect(QRectF(q.x() - 4, q.y() - 4, 8, 8))
        p.setBrush(Qt.NoBrush)
        p.setPen(QPen(QColor(230, 120, 30), 1, Qt.DashLine))
        for eje, valor in self.guias:
            a, bb = ((valor, -1e4), (valor, 1e4)) if eje == 0 else ((-1e4, valor), (1e4, valor))
            p.drawLine(self.l.a_px(*a), self.l.a_px(*bb))


class PanelObjetos(QFrame):
    """Propiedades contextuales: medidas esenciales y opciones avanzadas plegadas."""
    def __init__(self, control, parent=None):
        super().__init__(parent)
        self.control = control
        control.panel = self
        self.setObjectName("paleta_boceto")
        self.setFixedWidth(296)
        self._disponible = 660
        self._seleccion = ()
        self._sincronizada = None
        self._suspendido = False
        lay = QVBoxLayout(self)
        lay.setContentsMargins(6, 4, 6, 6)
        self.opciones = QToolButton(text="⋯", toolTip="Opciones de selección", popupMode=QToolButton.InstantPopup)
        menu = QMenu(self.opciones)
        menu.addAction("Seleccionar todos los objetos", self._todos)
        menu.addAction("Deseleccionar", self._ninguno)
        self.opciones.setMenu(menu)
        cab, _icono, titulo = armar_cabecera(self, None, extras=(self.opciones,))
        titulo.setText("Objetos vectoriales y texto")
        titulo.setToolTip("Objetos vectoriales y texto")
        lay.addWidget(cab)
        self.desplazador = QScrollArea()
        self.desplazador.setWidgetResizable(True)
        self.desplazador.setFrameShape(QFrame.NoFrame)
        self.desplazador.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        cuerpo = QWidget()
        c = QVBoxLayout(cuerpo)
        c.setContentsMargins(0, 0, 0, 0)
        c.setSpacing(5)
        self.perfiles = QCheckBox("Seleccionar perfiles CAD")
        self.perfiles.toggled.connect(self._perfiles)
        self.perfiles.setToolTip("Objeto: seleccionar y arrastrar el recurso completo. Perfiles CAD: elegir regiones para extruir o cortar.")
        c.addWidget(self.perfiles)
        self.indicacion = QLabel("Seleccioná un vector o texto para transformarlo", wordWrap=True)
        c.addWidget(self.indicacion)
        self.lista = QComboBox()
        self.lista.setAccessibleName("Objeto vectorial")
        self.lista.activated.connect(self._elegir)
        c.addWidget(self.lista)
        self.principal = QWidget()
        principal = QVBoxLayout(self.principal)
        principal.setContentsMargins(0, 0, 0, 0)
        principal.setSpacing(5)
        self.nombre = QLineEdit()
        self.nombre.setPlaceholderText("Nombre del objeto")
        self.nombre.setAccessibleName("Nombre del objeto")
        self.nombre.editingFinished.connect(self._nombre)
        principal.addWidget(self.nombre)
        fila = QHBoxLayout()
        self.tipo = QLabel()
        fila.addWidget(self.tipo, 1)
        self.visible = QCheckBox("Visible")
        self.visible.toggled.connect(self._visibilidad)
        fila.addWidget(self.visible)
        self.botones = {}
        bloquear = self._boton("Bloquear")
        fila.addWidget(bloquear)
        principal.addLayout(fila)
        self.transformacion = QWidget()
        transformacion = QVBoxLayout(self.transformacion)
        transformacion.setContentsMargins(0, 0, 0, 0)
        transformacion.setSpacing(4)
        transformacion.addWidget(QLabel("Transformar"))
        form = QFormLayout()
        form.setFieldGrowthPolicy(QFormLayout.AllNonFixedFieldsGrow)
        form.setHorizontalSpacing(8)
        form.setVerticalSpacing(4)
        self.campos = {}
        for clave, etiqueta in ETIQUETAS.items():
            campo = QLineEdit()
            campo.setMinimumWidth(0)
            campo.setAccessibleName(etiqueta)
            campo.setToolTip("Números, unidades y expresiones. Enter o Tab aplica; Esc restaura el valor anterior.")
            campo.textEdited.connect(lambda _t, k=clave: self._valor(k, previa=True))
            campo.editingFinished.connect(lambda k=clave: self._valor(k))
            campo.installEventFilter(self)
            self.campos[clave] = campo
            if clave in ("x", "y", "ancho", "alto", "angulo"):
                form.addRow(etiqueta, campo)
        transformacion.addLayout(form)
        self.proporciones = QCheckBox("Mantener proporciones")
        self.proporciones.setChecked(True)
        self.proporciones.toggled.connect(self._proporciones)
        transformacion.addWidget(self.proporciones)
        fila = QHBoxLayout()
        for nombre in ("Centrar", "Duplicar", "Restablecer"):
            fila.addWidget(self._boton(nombre))
        transformacion.addLayout(fila)
        self.texto = self._boton("Editar texto")
        transformacion.addWidget(self.texto)
        principal.addWidget(self.transformacion)
        self.avanzadas = Seccion("Opciones avanzadas", parent=self.principal)
        self.avanzadas.grilla.setColumnMinimumWidth(0, 0)
        opciones = QWidget()
        avanzado = QVBoxLayout(opciones)
        avanzado.setContentsMargins(0, 0, 0, 0)
        self.imanes = QCheckBox("Guías magnéticas (Ctrl las suspende)")
        self.imanes.setChecked(True)
        self.imanes.toggled.connect(lambda v: setattr(control, "snap", v))
        avanzado.addWidget(self.imanes)
        form = QFormLayout()
        for clave in ("sx", "sy", "px", "py"):
            form.addRow(ETIQUETAS[clave], self.campos[clave])
        avanzado.addLayout(form)
        self.pivotes = QComboBox()
        self.pivotes.addItems(("Centro de caja", "Centro geométrico", "Abajo izquierda", "Abajo centro", "Abajo derecha",
                              "Centro izquierda", "Centro derecha", "Arriba izquierda", "Arriba centro", "Arriba derecha"))
        self.pivotes.activated.connect(self._pivote)
        self.pivotes.setAccessibleName("Ubicación del pivote")
        avanzado.addWidget(self.pivotes)
        self.pivote_manual = QCheckBox("Editar pivote con el mouse")
        self.pivote_manual.toggled.connect(lambda v: setattr(control, "editar_pivote", v))
        avanzado.addWidget(self.pivote_manual)
        self.organizar = Seccion("Alinear, distribuir y agrupar")
        self.organizar.grilla.setColumnMinimumWidth(0, 0)
        organizacion = QWidget()
        org = QVBoxLayout(organizacion)
        org.setContentsMargins(0, 0, 0, 0)
        fila = QHBoxLayout()
        for nombre in ("Agrupar", "Desagrupar"):
            fila.addWidget(self._boton(nombre))
        org.addLayout(fila)
        self.alineacion = QComboBox()
        self.alineacion.addItems(list(ALINEACIONES))
        self.alineacion.currentIndexChanged.connect(self._disponibilidad_alinear)
        org.addWidget(self.alineacion)
        self.referencia = QComboBox()
        self.referencia.addItems(("Respecto de selección", "Respecto del origen", "Respecto del primer objeto"))
        self.referencia.currentIndexChanged.connect(self._disponibilidad_alinear)
        org.addWidget(self.referencia)
        self.separacion = QLineEdit()
        self.separacion.setPlaceholderText("Separación exacta (mm), opcional")
        self.separacion.textChanged.connect(self._disponibilidad_alinear)
        org.addWidget(self.separacion)
        self.b_alinear = QPushButton("Alinear / distribuir")
        self.b_alinear.clicked.connect(self._alinear)
        org.addWidget(self.b_alinear)
        self.organizar.grilla.addWidget(organizacion, 0, 0, 1, 2)
        avanzado.addWidget(self.organizar)
        self.geometria = Seccion("Geometría y validación")
        self.geometria.grilla.setColumnMinimumWidth(0, 0)
        geometria = QWidget()
        geo_lay = QVBoxLayout(geometria)
        geo_lay.setContentsMargins(0, 0, 0, 0)
        for acciones in (("Convertir texto", "Separar regiones"), ("Simplificar", "Unir perfiles")):
            fila = QHBoxLayout()
            for nombre in acciones:
                fila.addWidget(self._boton(nombre))
            geo_lay.addLayout(fila)
        geo_lay.addWidget(self._boton("Validar"))
        self.desfase = QLineEdit("1 mm")
        self.desfase.setAccessibleName("Desfase de contornos en mm")
        geo_lay.addWidget(self.desfase)
        self.esquinas = QComboBox()
        self.esquinas.addItems(("Esquinas redondas", "Esquinas vivas"))
        geo_lay.addWidget(self.esquinas)
        self.b_desfasar = QPushButton("Desfasar contornos")
        self.b_desfasar.clicked.connect(self._desfasar)
        geo_lay.addWidget(self.b_desfasar)
        self.geometria.grilla.addWidget(geometria, 0, 0, 1, 2)
        avanzado.addWidget(self.geometria)
        self.avanzadas.grilla.addWidget(opciones, 0, 0, 1, 2)
        principal.addWidget(self.avanzadas)
        c.addWidget(self.principal)
        self.error = QLabel(wordWrap=True)
        c.addWidget(self.error)
        c.addStretch()
        self.desplazador.setWidget(cuerpo)
        lay.addWidget(self.desplazador)
        for seccion in (self.avanzadas, self.organizar, self.geometria):
            seccion.plegada.connect(self._reubicar)
        self._lista_ids = None
        self.hide()

    def _boton(self, nombre):
        boton = QPushButton(nombre)
        boton.clicked.connect(lambda _v=False, n=nombre: self._accion(n))
        self.botones[nombre] = boton
        return boton

    def _reubicar(self, *_):
        self.ajustar_alto(self._disponible)
        area = self.parentWidget()
        if hasattr(area, "reubicar"):
            area.reubicar()

    def ajustar_alto(self, disponible):
        self._disponible = disponible
        natural = self.desplazador.widget().sizeHint().height() + self.layout().itemAt(0).widget().sizeHint().height() + 16
        self.setFixedHeight(max(80, min(natural, disponible)))

    def sincronizar(self):
        b, control = self.control.l.b, self.control
        firma = (id(b), control.l._generacion, tuple(control.l.seleccion), control.l.herramienta,
                 control.modo_perfiles, len(b.objetos), self._suspendido)
        if firma == self._sincronizada:
            return
        self._sincronizada = firma
        roots = ob.raices(b)
        firma = [(i, b.objetos[i]["nombre"], b.objetos[i]["bloqueado"], b.objetos[i]["visible"]) for i in roots]
        if firma != self._lista_ids:
            self._lista_ids = firma
            self.lista.blockSignals(True)
            self.lista.clear()
            for oid in roots:
                o = b.objetos[oid]
                self.lista.addItem(o["nombre"] + (" · bloqueado" if o["bloqueado"] else "")
                                   + (" · oculto" if not o["visible"] else ""), oid)
            self.lista.blockSignals(False)
        ids = control.seleccion()
        libres = [i for i in control.l.seleccion if i in b.curvas and i not in ob.indice(b)]
        self.setVisible(bool(roots or libres) and control.l.herramienta == "seleccionar" and not self._suspendido)
        bloqueo = any(b.objetos[i]["bloqueado"] for i in ids)
        self.principal.setVisible(bool(ids) or bool(libres))
        self.lista.setVisible(not ids or len(roots) > 1)
        self.lista.setCurrentIndex(self.lista.findData(ids[0]) if len(ids) == 1 else -1)
        self.perfiles.blockSignals(True)
        self.perfiles.setChecked(control.modo_perfiles)
        self.perfiles.blockSignals(False)
        self.indicacion.setText("Perfiles CAD: elegí regiones para extruir. Desactivá este modo para mover el objeto."
            if control.modo_perfiles else "Objeto bloqueado: desbloquealo para transformarlo." if bloqueo else
            "Seleccioná un vector o texto para transformarlo")
        self.indicacion.setVisible(not ids or bloqueo)
        for campo in self.campos.values():
            campo.setEnabled(bool(ids) and not bloqueo)
        self.transformacion.setEnabled(not bloqueo)
        self.avanzadas.setEnabled(not bloqueo)
        self.nombre.setEnabled(len(ids) == 1)
        cids = ob.curvas(b, ids) if ids else []
        textos = [i for i in cids if isinstance(b.curvas[i], Texto)]
        self.texto.setVisible(bool(textos))
        self.botones["Convertir texto"].setVisible(bool(textos))
        for nombre, boton in self.botones.items():
            aplica = bool(ids)
            motivo = "Seleccioná un objeto."
            if nombre == "Agrupar":
                aplica = len(ids) + len(libres) >= 2
                motivo = "Seleccioná al menos dos objetos con Mayús o Ctrl."
            elif nombre == "Desagrupar":
                aplica = any(any(h in b.objetos for h in b.objetos[i]["entidades"]) for i in ids)
                motivo = "La selección no contiene un grupo."
            elif nombre in ("Editar texto", "Convertir texto"):
                aplica = len(textos) == 1
                motivo = "Seleccioná un único texto editable."
            elif nombre in ("Separar regiones", "Simplificar"):
                aplica = len(ids) == 1 and not textos
                motivo = "Seleccioná un vector; convertí el texto antes de separar sus regiones."
            elif nombre == "Unir perfiles":
                aplica = len(ids) >= 2
                motivo = "Seleccioná al menos dos objetos con regiones cerradas."
            boton.setEnabled(aplica and (not bloqueo or nombre == "Bloquear"))
            boton.setToolTip(nombre if aplica else motivo)
        self._disponibilidad_alinear()
        self.b_desfasar.setEnabled(bool(ids) and not bloqueo)
        if not ids:
            self._seleccion = ()
            self._reubicar()
            return
        if tuple(ids) != self._seleccion:
            for campo in self.campos.values():
                campo.setModified(False)
            self.error.clear()
        self._seleccion = tuple(ids)
        if not self.nombre.hasFocus():
            self.nombre.setText(b.objetos[ids[0]]["nombre"] if len(ids) == 1 else f"{len(ids)} objetos")
        tipos = {b.objetos[i].get("tipo_origen", "SVG" if any("regla_relleno" in b.objetos[h] for h in b.objetos)
                  else "Vector") for i in ids}
        self.tipo.setText("Texto" if textos and len(textos) == len(cids) else
                          f"{len(ids)} objetos" if len(ids) > 1 else next(iter(tipos)))
        self.proporciones.blockSignals(True)
        self.proporciones.setChecked(all(b.objetos[i]["proporciones"] for i in ids))
        self.proporciones.blockSignals(False)
        self.visible.blockSignals(True)
        self.visible.setChecked(all(b.objetos[i]["visible"] for i in ids))
        self.visible.blockSignals(False)
        self.botones["Bloquear"].setText("Desbloquear" if all(b.objetos[i]["bloqueado"] for i in ids) else "Bloquear")
        self.actualizar_medidas()
        self._reubicar()

    def set_suspendido(self, activo):
        """Un diálogo de importación ocupa este contexto hasta aceptar o cancelar."""
        self._suspendido = activo
        self.sincronizar()

    def _disponibilidad_alinear(self, *_):
        ids = self.control.seleccion()
        if not hasattr(self, "b_alinear"):
            return
        distribuir = self.alineacion.currentText().startswith("Distribuir")
        minimo = 2 if self.separacion.text().strip() else 3
        aplica = len(ids) >= minimo if distribuir else (bool(ids) and
            (len(ids) >= 2 or self.referencia.currentIndex() == 1 or self.alineacion.currentText() == "Centrar en origen"))
        self.b_alinear.setEnabled(aplica)
        self.b_alinear.setToolTip("Aplicar a la selección" if aplica else
            "Distribuir requiere tres objetos o dos con separación exacta." if distribuir else
            "Elegí varios objetos o la referencia al origen.")

    def _todos(self):
        self.control.l.seleccion = ob.raices(self.control.l.b)
        self.control.l._notificar_seleccion()
        self.control.l.update()

    def _ninguno(self):
        self.control.l.seleccion = []
        self.control.l._notificar_seleccion()
        self.control.l.update()

    def actualizar_medidas(self):
        estado = self.control.estado()
        if estado is None:
            return
        for k, v in estado.items():
            if not self.campos[k].hasFocus() or not self.campos[k].isModified():
                texto = formato.numero(v)
                if texto != self.campos[k].text():
                    self.campos[k].setText(texto)

    def eventFilter(self, campo, e):
        if campo in self.campos.values() and e.type() == QEvent.ShortcutOverride and e.key() == Qt.Key_Escape:
            e.accept()
            return True
        if campo in self.campos.values() and e.type() == QEvent.KeyPress and e.key() == Qt.Key_Escape:
            campo.setModified(False)
            self.control.cancelar()
            self.error.clear()
            estado = self.control.estado()
            if estado is not None:
                clave = next(k for k, v in self.campos.items() if v is campo)
                campo.setText(formato.numero(estado[clave]))
            return True
        return super().eventFilter(campo, e)

    def _elegir(self, indice):
        oid = self.lista.itemData(indice)
        if oid is None:
            return
        self.control.set_modo_perfiles(False)
        self.control.l.seleccion = [oid]
        self.control.l.perfiles_sel = []
        self.control.l._notificar_seleccion()
        self.control.l.update()

    def _perfiles(self, activo):
        self.control.set_modo_perfiles(activo)

    def _nombre(self):
        ids = self.control.seleccion()
        if (self.nombre.isModified() and len(ids) == 1 and self.nombre.text().strip()
                and self.nombre.text() != self.control.l.b.objetos[ids[0]]["nombre"]):
            self.control.aplicar(lambda: self.control.l.b.objetos[ids[0]].update(nombre=self.nombre.text().strip()))
            self.nombre.setModified(False)

    def _proporciones(self, activo):
        ids = self.control.seleccion()
        if ids:
            self.control.aplicar(lambda: [self.control.l.b.objetos[i].update(proporciones=activo) for i in ids])

    def _visibilidad(self, visible):
        ids = self.control.seleccion()
        if ids:
            self.control.aplicar(lambda: [self.control.l.b.objetos[i].update(visible=visible) for i in ids])

    def _valor(self, clave, previa=False):
        c = self.control
        if not c.seleccion() or not self.campos[clave].isModified() and not previa:
            return
        c.previa = None
        try:
            valor = c.l.evaluar(self.campos[clave].text(), ANGULO if clave == "angulo" else
                               ESCALAR if clave in ("sx", "sy") else LONGITUD, estricto=True)
            m, p = c.matriz_campo(clave, valor)
            if m is not None:
                x0, y0, x1, y1 = c.caja()
                limites = np.array(((x0, y0), (x1, y0), (x1, y1), (x0, y1))) @ m[:2, :2].T + m[:2, 2]
                if not np.isfinite(limites).all() or abs(limites).max() > 1e6:
                    raise ErrorBoceto("El objeto transformado supera 1 km desde el origen del boceto.")
            self.error.clear()
            if previa:
                c.previa, c.previa_pivote = m, p
                if c.l.visor is not None:
                    c.l.visor.set_perfiles([])
                c.l.update()
                return
            c.previa_pivote = None
            c.confirmar_campo(clave, valor, self.campos[clave].text())
            self.campos[clave].setModified(False)
            self.actualizar_medidas()
        except (ErrorBoceto, ErrorExpresion, ValueError) as e:
            self.error.setText(str(e))
            c.previa = c.previa_pivote = None
            c.l.cambio.emit()
            c.l.update()

    def _pivote(self, indice):
        c, b = self.control, self.control.l.b
        if not c.seleccion():
            return
        x0, y0, x1, y1 = c.caja()
        puntos = (((x0 + x1) / 2, (y0 + y1) / 2), None, (x0, y0), ((x0 + x1) / 2, y0), (x1, y0),
                  (x0, (y0 + y1) / 2), (x1, (y0 + y1) / 2), (x0, y1), ((x0 + x1) / 2, y1), (x1, y1))
        p = puntos[indice]
        if p is None:
            from ..nucleo import geometria as geo
            from ..nucleo.perfiles import sin_huecos
            ids = set(ob.curvas(b, c.seleccion()))
            try:
                perfiles = [p for p in sin_huecos(c.l._perfiles(), b) if p.firma <= ids]
            except geo.ErrorGeometria as e:
                self.error.setText(str(e))
                return
            area = sum(p.area for p in perfiles)
            p = tuple(sum(p.area * p.centroide_uv[k] for p in perfiles) / area for k in (0, 1)) if area else puntos[0]
        c.aplicar(lambda: [ob.poner_pivote(b, i, p) for i in c.seleccion()])

    def _accion(self, nombre):
        self.error.clear()
        try:
            self._ejecutar_accion(nombre)
        except (ValueError, ErrorBoceto) as e:
            self.error.setText(str(e))

    def _ejecutar_accion(self, nombre):
        c, b = self.control, self.control.l.b
        ids = c.seleccion()
        if nombre == "Centrar" and ids:
            c.aplicar(lambda: ob.alinear(b, ids, "origen"))
        elif nombre == "Restablecer" and ids:
            c.aplicar(lambda: ob.restablecer(b, ids))
        elif nombre == "Agrupar":
            elementos = ids + [i for i in c.l.seleccion if i in b.curvas and i not in ob.indice(b)]
            def agrupar():
                c.l.seleccion = [ob.crear(b, elementos, "Grupo")]
            c.aplicar(agrupar)
        elif nombre == "Desagrupar":
            def separar():
                c.l.seleccion = [h for i in ids for h in ob.desagrupar(b, i)]
            hojas = [i for i in ids if not any(h in b.objetos for h in b.objetos[i]["entidades"])]
            if not ids:
                pass
            elif len(hojas) == len(ids):
                # Una forma (un elemento del SVG) no se separa: sus curvas juntas son el contorno cerrado.
                self.error.setText("Esta forma es un objeto: sus curvas no se separan para no romper el contorno.")
            else:
                c.aplicar(separar)
        elif nombre == "Duplicar":
            if ids:
                def copiar():
                    from ..timeline.operaciones import _contenido_texto, texto_con_valores
                    c.l.seleccion = ob.duplicar(b, ids)
                    valores = c.l.valores_parametros()
                    for i in ob.curvas(b, c.l.seleccion):
                        t = b.curvas[i]
                        if isinstance(t, Texto):
                            t.texto = texto_con_valores(_contenido_texto(t, valores), valores)
                            t.parametro_texto = t.parametro_altura = t.altura_expr = None
                c.aplicar(copiar)
        elif nombre == "Bloquear" and ids:
            c.aplicar(lambda: [b.objetos[i].update(bloqueado=not b.objetos[i]["bloqueado"]) for i in ids])
        elif nombre in ("Editar texto", "Convertir texto") and ids:
            textos = [i for i in ob.curvas(b, ids) if isinstance(b.curvas[i], Texto)]
            if not textos:
                self.error.setText("Elegí un objeto de texto editable.")
            elif nombre == "Editar texto":
                c.l.editar_texto(textos[0], c.l.a_px(*ob.pivote(b, ids[0])))
            else:
                from ..timeline.operaciones import _contenido_texto, texto_con_valores
                def convertir():
                    valores = c.l.valores_parametros()
                    for i in textos:
                        b.curvas[i].texto = texto_con_valores(_contenido_texto(b.curvas[i], valores), valores)
                        b.desglosar_texto(i)
                c.aplicar(convertir)
        elif nombre == "Separar regiones" and len(ids) == 1:
            from ..api.herramientas_objetos_vectoriales import separar_regiones
            def separar_islas():
                c.l.seleccion = separar_regiones(b, c.l._plano_perfiles(), ids[0])
            c.aplicar(separar_islas)
        elif nombre == "Validar" and ids:
            from ..api.herramientas_objetos_vectoriales import validar_objetos
            r = validar_objetos(b, c.l._plano_perfiles(), ids)
            self.error.setText("Perfiles válidos: " + str(len(r["usable_profiles"])) if r["valid"] else
                               " ".join(r["messages"]) or "Hay geometría inválida en el objeto.")
        elif nombre == "Simplificar" and len(ids) == 1:
            def simplificar():
                r = ob.simplificar(b, ids[0])
                self.error.setText(f"{r['removed']} trazos redundantes menos · desvío {r['measured_deviation_mm']:.6g} mm")
            c.aplicar(simplificar)
        elif nombre == "Unir perfiles" and ids:
            from ..api.herramientas_objetos_vectoriales import combinar
            def unir():
                c.l.seleccion = [combinar(b, c.l._plano_perfiles(), ids)]
            c.aplicar(unir)

    def _alinear(self):
        c = self.control
        ids = c.seleccion()
        try:
            ref = ("seleccion", "origen", "objeto")[self.referencia.currentIndex()]
            gap = c.l.evaluar(self.separacion.text()) if self.separacion.text().strip() else None
            c.aplicar(lambda: ob.alinear(c.l.b, ids, ALINEACIONES[self.alineacion.currentText()], ref,
                                         ids[0] if ref == "objeto" and ids else None, gap))
        except (ErrorExpresion, ErrorBoceto) as e:
            self.error.setText(str(e))

    def _desfasar(self):
        from ..api.herramientas_objetos_vectoriales import desfasar
        c = self.control
        try:
            distancia = c.l.evaluar(self.desfase.text())
            def aplicar():
                nuevo = desfasar(c.l.b, c.l._plano_perfiles(), c.seleccion(), distancia,
                                 "vivas" if self.esquinas.currentIndex() else "redondas")
                c.l.seleccion = [nuevo]
            c.aplicar(aplicar)
        except (ErrorBoceto, ErrorExpresion) as e:
            self.error.setText(str(e))
