# -*- coding: utf-8 -*-
"""El manipulador del boceto sobre recursos terminados, sin entrar en edición ni retroceder el timeline."""
from PySide6.QtCore import QEvent, QObject, Qt, QTimer
from PySide6.QtGui import QPainter, QPen, QColor

from .. import api
from ..api.errores import ErrorAPI, error
from ..api.herramientas_boceto import actualizar_alturas_texto, soltar_parametros_texto, parametros_de_textos
from ..restricciones import ErrorBoceto, objetos as ob
from ..timeline.parametros import ANGULO, ESCALAR, LONGITUD
from .editor_boceto import Lienzo
from .objetos_vectoriales import PanelObjetos


class LienzoVectorial(Lienzo):
    """Vista de una copia: el gesto provisional no toca el documento; confirmar reemplaza un solo OpBoceto."""

    def __init__(self, gestor, br):
        self.gestor, self.op_id, self.br = gestor, br.op_id, None
        v = gestor.v
        self.documento = v.doc
        super().__init__(br.boceto.copia(), lambda *a: v.doc.parametros.evaluar(*a), v.area,
                         visor=v.visor, plano=br.plano)
        self.setAttribute(Qt.WA_TransparentForMouseEvents)
        self.valores_parametros = lambda: v.doc.parametros.valores()
        self.mensaje.connect(v.mensaje)
        self.objetos.panel = PanelObjetos(self.objetos, v.area)
        self.cargar(br)
        self.hide()

    def cargar(self, br):
        if self.br is br:
            return
        self.br, self.plano = br, br.plano
        b = self.gestor.v.doc.operacion(self.op_id).boceto.copia()
        actualizar_alturas_texto(b, br)
        # Las coordenadas son las resueltas; el contenido del texto conserva su plantilla paramétrica.
        for i, p in b.puntos.items():
            if i in br.boceto.puntos:
                p.x, p.y = br.boceto.coords(i)
        ob.evaluar(b, lambda valor, k: self.evaluar(valor, ANGULO if k == "angulo" else
                    ESCALAR if k in ("sx", "sy") else LONGITUD))
        self.b.__dict__.update(b.__dict__)
        ob.invalidar(self.b)
        self.objetos._firma = None
        self._indice_inf = None
        self.seleccion = [i for i in self.seleccion if i in self.b.objetos]
        self.resultado = br.solver
        self._generacion += 1
        self.objetos.notificar()
        self.update()

    def aplicar_cambio(self, funcion, operacion=False, anclar=True):
        v = self.gestor.v
        if v.doc is not self.documento:
            return False  # un editingFinished pendiente del documento anterior no llega al nuevo
        antes, seleccion = self.b.a_dict(), list(self.seleccion)
        try:
            funcion()  # el documento valida y resuelve al confirmar; no se repite antes en la copia visual
        except (ErrorBoceto, ValueError) as e:
            self._restaurar(antes)
            self.seleccion = seleccion
            self.mensaje.emit(str(e))
            return False
        if self.b.a_dict() == antes:
            self.historial.clear()
            return True
        op = v.doc.operacion(self.op_id)
        nueva = op.copia()
        nueva.boceto = self.b.copia()
        self.gestor.aplicando = True
        try:
            with api.Sesion(v.doc).transaccion():
                v.doc.reemplazar(op.id, nueva)
                soltar_parametros_texto(v.doc, parametros_de_textos(op.boceto), nueva.boceto)
        except (ErrorAPI, ValueError) as e:
            self._restaurar(antes)
            self.seleccion = seleccion
            self.mensaje.emit(str(e))
            return False
        finally:
            self.gestor.aplicando = False
            self.historial.clear()
            self.pila_rehacer.clear()
            self.cargar(v.doc.estado_final.bocetos[self.op_id])
        return True

    def _notificar_seleccion(self):
        super()._notificar_seleccion()
        if self.gestor.activo is self:
            self.gestor.notificar_seleccion()

    def editar_texto(self, cid, _pos):
        v, op_id = self.gestor.v, self.op_id
        def abrir():
            v.editar_operacion(op_id)
            if v.modo_boceto.activo:
                lz = v.modo_boceto.lienzo
                lz.editar_texto(cid, lz.a_px(*ob.pivote(lz.b, ob.indice(lz.b)[cid][0])))
        QTimer.singleShot(0, v, abrir)

    def paintEvent(self, _e):
        self._camara()
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        internos = ob.indice(self.b)
        p.setPen(QPen(QColor(90, 160, 255), 1.5))
        for c in self.b.curvas.values():
            if c.id not in internos and self._visible(c):
                for poli in self._polilineas(c):
                    self._dibujar_polilinea(p, poli)
        self.objetos.dibujar(p)
        p.end()


class VectoresEnVista(QObject):
    """Da prioridad al objeto solo en selección libre; un comando CAD conserva la propiedad de sus clics."""

    def __init__(self, ventana):
        super().__init__(ventana)
        self.v, self.activo, self.capas = ventana, None, {}
        self.aplicando = False
        self.doc = None
        ventana.visor.installEventFilter(self)
        ventana.installEventFilter(self)

    def disponible(self):
        return self.v.panel is None and not self.v.modo_boceto.activo and not self.v.area.multiples

    def sincronizar(self, estado, ocultos):
        if self.aplicando:
            return (self.activo.op_id,) if self.activo is not None else ()
        if self.doc is not self.v.doc:
            self.doc = self.v.doc
            self.activo = None
            for lz in self.capas.values():
                lz.hide()
                lz.objetos.panel.hide()
                lz.objetos.panel.deleteLater()
                lz.deleteLater()
            self.capas.clear()
            self.v.area.panel_objetos = None
        vivos = {k: br for k, br in estado.bocetos.items() if br.boceto.objetos and k not in ocultos
                 and any(o.id == k and hasattr(o, "boceto") for o in self.v.doc.operaciones)}
        for k in list(self.capas):
            if k not in vivos:
                lz = self.capas.pop(k)
                if self.activo is lz:
                    self.activo = None
                    self.v.area.panel_objetos = None
                lz.objetos.panel.hide()
                lz.hide()
                lz.objetos.panel.deleteLater()
                lz.deleteLater()
        if self.disponible():
            for k, br in vivos.items():
                if k not in self.capas:
                    self.capas[k] = LienzoVectorial(self, br)
                self.capas[k].cargar(br)
        for lz in self.capas.values():
            mostrar = self.disponible() and lz is self.activo
            lz.setGeometry(self.v.visor.geometry())
            lz.setVisible(mostrar)
            lz.objetos.panel.setVisible(mostrar)
            if mostrar:
                lz.raise_()
                lz.objetos.notificar()
        return (self.activo.op_id,) if self.disponible() and self.activo is not None else ()

    def seleccionar(self, sketch, ids, modo="replace"):
        """Selección por navegador o puente, sobre la misma representación que recibe el ratón."""
        if not self.disponible():
            raise error("APP_BUSY", "Terminá el comando o el boceto antes de seleccionar el vector.")
        lz = self.capas.get(sketch)
        if lz is None or any(i not in ob.raices(lz.b) for i in ids):
            raise error("ENTITY_NOT_FOUND", "Elegí objetos raíz del boceto disponible.")
        self._activar(lz)
        actuales = lz.objetos.seleccion()
        lz.objetos.modo_perfiles = False
        lz.perfiles_sel = []
        lz.seleccion = (list(dict.fromkeys(actuales + ids)) if modo == "add" else
                        [i for i in actuales if i not in ids] if modo == "remove" else list(ids))
        lz._notificar_seleccion()
        lz.update()
        return {"objects": list(lz.seleccion), "count": len(lz.seleccion)}

    def _activar(self, lz):
        if self.activo is not lz:
            if self.activo is not None:
                self.activo.objetos.cancelar()
                self.activo.hide()
                self.activo.objetos.panel.hide()
            self.activo = lz
            self.v.area.panel_objetos = lz.objetos.panel
            self.v._seleccionar([])
            self.v._refrescar_visibilidad()
        self.v.area.reubicar()

    def notificar_seleccion(self):
        lz = self.activo
        if lz is not None:
            if not lz.objetos.modo_perfiles and self.v.seleccion:
                self.v._seleccionar([])
            self.v.navegador.seleccionar([lz.op_id], revelar=False)
            self.v.info_seleccion(lz.describir_seleccion())

    def eventFilter(self, origen, e):
        lz = self.activo
        tipo = e.type()
        panel = self.v.panel
        if (origen is self.v.visor and panel is not None and
                getattr(panel.comando, "EN_BOCETO_ABIERTO", False) and
                tipo in (QEvent.ShortcutOverride, QEvent.KeyPress) and
                e.key() in (Qt.Key_Escape, Qt.Key_Return, Qt.Key_Enter)):
            if tipo == QEvent.ShortcutOverride:
                e.accept()
            else:
                panel.keyPressEvent(e)
            return True
        if tipo == QEvent.WindowDeactivate and lz is not None:
            lz.objetos.cancelar()
        if origen is not self.v.visor or not self.disponible():
            return False
        if tipo == QEvent.Resize:
            for capa in self.capas.values():
                capa.setGeometry(self.v.visor.geometry())
        if tipo in (QEvent.ShortcutOverride, QEvent.KeyPress) and e.key() == Qt.Key_Escape and lz is not None:
            if tipo == QEvent.ShortcutOverride:
                e.accept()
            else:
                lz.objetos.cancelar()
            return True
        if lz is not None and lz.objetos.arrastre is not None:
            if tipo == QEvent.MouseMove:
                lz.mouseMoveEvent(e)
                return True
            if tipo == QEvent.MouseButtonRelease:
                lz.mouseReleaseEvent(e)
                return True
            if tipo == QEvent.MouseButtonPress:
                lz.objetos.cancelar()
                return True
        if tipo != QEvent.MouseButtonPress or e.button() != Qt.LeftButton or self.v.visor.modo is not None:
            return False
        if lz is not None and lz.objetos.modo_perfiles:
            return False
        pos = e.position()
        if lz is not None and lz.objetos.manija_en(pos) is not None:
            lz.mousePressEvent(e)
            return True
        for capa in reversed(list(self.capas.values())):
            capa._camara()
            if capa.objetos.en(pos) is None:
                continue
            p = self.v.visor.interseccion_plano(pos, capa.plano)
            cara = self.v.visor.elegir_entidad(pos, {"cara"})
            if p is None or (cara is not None and float((p - self.v.visor.rayo(pos)[0]) @
                    self.v.visor.rayo(pos)[1]) > cara["t"] + 1e-6):
                continue
            self._activar(capa)
            capa.mousePressEvent(e)
            return True
        if lz is not None:
            lz.seleccion = []
            lz._notificar_seleccion()
            lz.update()
        return False
