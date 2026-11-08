# -*- coding: utf-8 -*-
"""Escala y Mover/copiar del boceto con su panel (Fusion: Modify › Scale y Modify › Move/Copy).

Antes se manejaban con «elegí la geometría, Enter, clic en el punto base y una caja flotante»: nada en pantalla decía
que había que apretar Enter. Acá el estado vive en un controlador y la persona lo maneja desde `ui/panel_transformar.py`,
desde el dibujo (clic en la geometría, en el punto base y en el destino, el asa del factor) o con las dos cosas a la vez:
los campos del panel son la única fuente de los valores y las asas escriben en ellos.

La vista previa se calcula con la misma transformación del núcleo (`Boceto.escalar` / `Boceto.transformar`), que además
se prueba sobre una copia del boceto: si el núcleo la rechaza (geometría fija, factor imposible), el panel lo dice antes
de aceptar. Cancelar no toca el boceto."""
import math
from types import SimpleNamespace

from PySide6.QtCore import QPointF, Qt
from PySide6.QtGui import QColor, QPen

from ..restricciones import ErrorBoceto
from ..restricciones.boceto import MEDIDA_MAXIMA
from ..timeline.parametros import ANGULO, ESCALAR, LONGITUD, ErrorExpresion
from . import formato
from .asas_boceto import GestorAsas2D, asas_escala, asas_mover, centro_de, polilineas_de
from .patron_boceto import _Mal

HERRAMIENTAS = ("escala", "mover")
ETIQUETAS = {"factor": "Factor", "dx": "ΔX", "dy": "ΔY", "angulo": "Ángulo", "base_x": "Base X", "base_y": "Base Y"}
DEFECTO = {"escala": {"factor": "2", "base_x": "", "base_y": ""},
           "mover": {"dx": "0", "dy": "0", "angulo": "0", "copiar": False, "base_x": "", "base_y": ""}}


def aplicar(b, ids, p):
    """Hace sobre el boceto `b` lo que describen los parámetros `p` (la vista previa, la validación y Aceptar usan esto)."""
    if "factor" in p:
        b.escalar(ids, p["base"], p["factor"])
    else:
        b.transformar(ids, p["dx"], p["dy"], p["angulo"], p["base"], p["copiar"])


def _funcion(p):
    """Punto → punto de la misma transformación que `aplicar`, para dibujar la vista previa sin tocar el boceto."""
    bx, by = p["base"]
    if "factor" in p:
        f = p["factor"]
        return lambda q: (bx + f * (q[0] - bx), by + f * (q[1] - by))
    c, s = math.cos(math.radians(p["angulo"])), math.sin(math.radians(p["angulo"]))
    return lambda q: (bx + c * (q[0] - bx) - s * (q[1] - by) + p["dx"], by + s * (q[0] - bx) + c * (q[1] - by) + p["dy"])


class ControlTransformar:
    """Estado y comportamiento de las herramientas Escala y Mover/copiar de un `Lienzo`."""

    def __init__(self, lienzo):
        self.l = lienzo
        self.panel = None            # lo conecta ModoBoceto
        self.tipo = None
        self.campo = "seleccion"     # qué llena el próximo clic: seleccion, base o destino (Mover)
        self.base = None             # None o (x, y)
        self.textos = {}
        self.previa = True
        self.error_clic = ""
        self._cache = self._firma = self._estado = None

    @property
    def activo(self):
        return self.tipo is not None and self.l.herramienta in HERRAMIENTAS

    # ------------------------------------------------------------ arranque y cierre
    def iniciar(self, herramienta):
        """Al elegir la herramienta: estado nuevo. Con algo ya elegido salta al punto base."""
        self.cerrar()
        self.tipo = herramienta
        self.textos = dict(DEFECTO[herramienta])
        if herramienta == "mover":
            self.textos["copiar"] = bool(self.l.opciones.get("copiar"))
        self.l.fase = self.campo = "seleccion"
        if self.l._seleccion_util():
            self.l.fase = self.campo = "base"
        self._emitir()

    def cerrar(self):
        """Suelta todo (también las asas): no queda geometría ni estado a medias."""
        if self.l._asas is not None and getattr(self.l._asas, "_de_transformar", False):
            self.l._asas.cerrar()
            self.l._asas = None
        self.tipo = self.base = self._cache = self._firma = self._estado = None
        self.previa, self.error_clic = True, ""

    # ------------------------------------------------------------ valores
    def recibir(self, textos):
        """Los campos del panel cambiaron (tecla, casilla): se evalúa de nuevo y se repinta."""
        antes, self.textos = self.textos, dict(textos)
        if self.tipo == "mover":
            self.l.opciones["copiar"] = bool(textos.get("copiar"))
        if (textos.get("base_x"), textos.get("base_y")) != (antes.get("base_x"), antes.get("base_y")):
            xy = [self._numero_o_none(k) for k in ("base_x", "base_y")]
            if None not in xy:
                self.base = (xy[0], xy[1])
            elif not any(str(textos.get(k, "")).strip() for k in ("base_x", "base_y")):
                self.base = None                              # los dos campos vacíos: sin punto base
        self._emitir()
        self.l.update()

    def _numero_o_none(self, clave, tipo=LONGITUD):
        try:
            return float(self.l.evaluar(str(self.textos.get(clave, "")).strip(), tipo))
        except (ErrorExpresion, ValueError, ZeroDivisionError):
            return None

    def _numero(self, clave, tipo=LONGITUD):
        texto = str(self.textos.get(clave, "")).strip()
        if not texto:
            raise _Mal(clave, f"Falta el valor de «{ETIQUETAS[clave]}».")
        try:
            v = float(self.l.evaluar(texto, tipo))
        except (ErrorExpresion, ValueError, ZeroDivisionError) as e:
            raise _Mal(clave, f"«{ETIQUETAS[clave]}»: {e}") from e
        if not math.isfinite(v):
            raise _Mal(clave, f"«{ETIQUETAS[clave]}» tiene que ser un número finito.")
        return v

    def parametros(self, ids):
        """Los parámetros del núcleo con lo que hay en los campos, o `_Mal`. Mover sin punto base gira alrededor del centro
        de lo elegido (como Fusion); Escala sí lo exige."""
        if self.base is None and self.tipo == "escala":
            raise _Mal("", "Elegí el punto base: clic en un punto del dibujo o en el origen.")
        base = self.base or centro_de(self.l, ids)
        if self.tipo == "escala":
            f = self._numero("factor", ESCALAR)
            if f <= 0:
                raise _Mal("factor", "El factor de escala debe ser positivo.")
            return {"base": base, "factor": f}
        return {"base": base, "dx": self._numero("dx"), "dy": self._numero("dy"), "angulo": self._numero("angulo", ANGULO),
                "copiar": bool(self.textos.get("copiar"))}

    def calcular(self):
        """{params, error, malos, polis, falta}: se rehace solo si cambió algo que importa (campos, elegido, boceto)."""
        l = self.l
        ids = l._seleccion_util()
        clave = (self.tipo, tuple(ids), tuple(sorted(self.textos.items())), self.base, l._generacion)
        if self._cache is not None and self._cache[0] == clave:
            return self._cache[1]
        r = {"params": None, "error": "", "malos": set(), "polis": [], "falta": False}
        try:
            if not ids:
                r["falta"] = True
                raise _Mal("", "Elegí la geometría: clic en cada curva o una ventana de selección.")
            p = self.parametros(ids)
            if "factor" in p:                                  # el núcleo la rechaza acá, no al aceptar (sin copiar el boceto)
                l.b.comprobar_escalar(ids, p["base"])
            elif not p["copiar"]:
                l.b.comprobar_mover(ids)
            f = _funcion(p)
            polis = [[f(q) for q in poli] for poli in polilineas_de(l, ids)]
            if any(abs(v) > MEDIDA_MAXIMA for poli in polis for q in poli for v in q):
                raise _Mal("factor" if self.tipo == "escala" else "dx",
                           f"El resultado pasaría de {MEDIDA_MAXIMA / 1e6:g} km del origen: elegí un valor menor.")
            r["params"], r["polis"] = p, polis
        except _Mal as e:
            r["error"], r["malos"] = str(e), {e.clave} if e.clave else set()
            r["falta"] = r["falta"] or not e.clave
        except ErrorBoceto as e:
            r["error"] = str(e)
        self._cache = (clave, r)
        return r

    # ------------------------------------------------------------ estado para el panel
    def _texto_base(self):
        b = self.base
        self.textos["base_x"], self.textos["base_y"] = (formato.numero(b[0]), formato.numero(b[1])) if b is not None else ("", "")

    def _etiqueta_base(self):
        c = self.base
        if c is None:
            return "Centro de la selección" if self.tipo == "mover" else ""
        return "Origen" if math.hypot(*c) < 1e-9 else "(%s, %s)" % (formato.numero(c[0]), formato.numero(c[1]))

    def _etiqueta_destino(self):
        """«(x, y)» del destino que dan ΔX y ΔY desde el punto base, o vacío si todavía no se movió nada."""
        d = [self._numero_o_none(k) for k in ("dx", "dy")]
        if self.base is None or None in d or math.hypot(*d) < 1e-9:
            return ""
        return "(%s, %s)" % (formato.numero(self.base[0] + d[0]), formato.numero(self.base[1] + d[1]))

    def estado(self):
        """Lo que muestra el panel: conteos de cada selección, campo activo, valores, qué falta y qué reparo hay."""
        l, r = self.l, self.calcular()
        guia = ""
        if r["falta"] and not r["error"].startswith("Elegí el punto base"):
            guia = r["error"]
        elif self.campo == "base" and self.base is None:
            guia = "Elegí el punto base: clic en un punto del dibujo o en el origen."
        elif self.campo == "destino":
            guia = "Clic en el destino (o escribí ΔX, ΔY y el ángulo)."
        elif not r["error"]:
            guia = "Enter acepta y Esc cancela."
        error = r["error"] if not r["falta"] else ""
        if self.error_clic:
            error = self.error_clic
        return {"tipo": self.tipo, "campo": self.campo,
                "conteos": {"seleccion": len(l._seleccion_util()), "base": int(self.base is not None),
                            "destino": int(bool(self._etiqueta_destino()))},
                "etiquetas": {"base": self._etiqueta_base(), "destino": self._etiqueta_destino()}, "campos": dict(self.textos), "malos": set(r["malos"]),
                "valido": r["params"] is not None and not r["error"], "guia": guia if not error else "", "error": error,
                "previa": self.previa}

    def _emitir(self):
        """Le manda el estado al panel (solo si cambió) y deja las asas listas."""
        if not self.activo or self.panel is None:
            return
        firma = (tuple(self.l._seleccion_util()), self.campo, self.base)
        if firma != self._firma:
            self._firma, self.error_clic = firma, ""
        estado = self.estado()
        if estado != self._estado:
            self._estado = estado
            self.panel.mostrar(estado)
        self._armar_asas()

    def notificar(self):
        """El Lienzo avisa que cambió la selección o el boceto."""
        self._emitir()

    # ------------------------------------------------------------ campos y clics
    def elegir_campo(self, campo):
        """Panel: lo que llena el próximo clic."""
        if campo != "seleccion" and not self.l._seleccion_util():
            self.error_clic = "Primero elegí la geometría."
        elif campo == "destino" and self.base is None:
            self.error_clic = "Primero elegí el punto base."
        else:
            self.error_clic = ""
            self.l.fase = self.campo = campo
        self._emitir()
        self.l.update()

    def limpiar_campo(self, campo):
        """La ✕ de un campo lo vacía y lo deja listo para elegir de nuevo."""
        if campo == "seleccion":
            self.l.seleccion = []
        elif campo == "destino":
            self.textos["dx"] = self.textos["dy"] = "0"
        else:
            self.base = None
            self._texto_base()
        self.l.fase = self.campo = campo
        self._emitir()
        self.l.update()

    def set_previa(self, activa):
        self.previa = bool(activa)
        self._emitir()
        self.l.update()

    def clic(self, pos):
        """Clic de posición del campo activo (punto base o destino). True si lo usó."""
        l = self.l
        _pid, xy = l._ajustar(pos)
        if self.campo == "base":
            self.base = (round(xy[0], 9), round(xy[1], 9))
            self._texto_base()
            self.error_clic = ""
            if self.tipo == "mover":
                self.l.fase = self.campo = "destino"           # el siguiente clic es el destino
            self._emitir()
            return True
        if self.campo == "destino":
            self.textos["dx"], self.textos["dy"] = formato.numero(xy[0] - self.base[0]), formato.numero(xy[1] - self.base[1])
            self._cache = None
            self._emitir()
            return True
        return False

    def enter(self):
        """Enter: con la geometría recién elegida pasa al punto base; con todo bien acepta; si no, dice qué falta."""
        e = self.estado()
        if self.campo == "seleccion" and self.l._seleccion_util():
            self.elegir_campo("base")
        elif e["valido"]:
            self.aceptar()
        else:
            self.l.mensaje.emit(e["error"] or e["guia"])

    # ------------------------------------------------------------ aceptar y cancelar
    def aceptar(self):
        """Aceptar (botón, Enter o Enter en un campo): aplica en UN paso de deshacer y sale."""
        l, e = self.l, self.estado()
        if not e["valido"]:
            l.mensaje.emit(e["error"] or e["guia"])
            return False
        p, ids = self.calcular()["params"], l._seleccion_util()
        if not l.aplicar_movimiento(lambda: aplicar(l.b, ids, p), [] if p.get("copiar") else ids, _funcion(p)):
            return False
        l.seleccion = []
        l.set_herramienta("seleccionar")
        return True

    def cancelar(self):
        """Cancelar (botón, ✕ o Esc): sale sin tocar el boceto."""
        self.l.set_herramienta("seleccionar")

    # ------------------------------------------------------------ dibujo
    def dibujar(self, p, acento):
        """El punto base, la vista previa (siguiendo al cursor mientras se elige el destino) y nada más."""
        l, r = self.l, self.calcular()
        if self.base is not None:
            q = l.a_px(*self.base)
            p.setPen(QPen(QColor(255, 140, 0), 2))
            p.drawEllipse(q, 7, 7)
            p.drawLine(QPointF(q.x() - 11, q.y()), QPointF(q.x() + 11, q.y()))
            p.drawLine(QPointF(q.x(), q.y() - 11), QPointF(q.x(), q.y() + 11))
        polis = r["polis"]
        if self.campo == "destino" and l.cursor is not None and self.base is not None and r["params"] is not None:
            f = _funcion(dict(r["params"], dx=l.cursor[0] - self.base[0], dy=l.cursor[1] - self.base[1]))
            polis = [[f(q) for q in poli] for poli in polilineas_de(l, l._seleccion_util())]
        if self.previa and polis:
            p.setPen(QPen(acento, 2.0, Qt.DashLine))
            for poli in polis:
                l._dibujar_polilinea(p, poli)

    # ------------------------------------------------------------ asas
    def _armar_asas(self):
        """Las asas atadas a los campos del panel: el factor (Escala) o ΔX/ΔY y el ángulo (Mover). Se rehacen solo si cambió
        la geometría o el punto base."""
        l = self.l
        r = self.calcular() if self.activo else None
        if r is None or r["params"] is None or self.panel is None or self.base is None:     # sin base elegida el asa taparía su clic
            if l._asas is not None and getattr(l._asas, "_de_transformar", False):
                l._asas.cerrar()
                l._asas = None
            return
        if l._asas is not None and not getattr(l._asas, "_de_transformar", False):
            return                                        # otra herramienta con sus propias asas
        base = r["params"]["base"]
        clave = (self.tipo, tuple(l._seleccion_util()), base)
        if l._asas is not None and getattr(l._asas, "_clave", None) == clave:
            return
        if l._asas is not None:
            l._asas.cerrar()
        if self.tipo == "escala":
            asas, tipos, _previa = asas_escala(l, l._seleccion_util(), base)
            campos = [self.panel.campos["factor"]]
        else:
            asas, tipos, _previa = asas_mover(l, l._seleccion_util(), base)
            campos = [self.panel.campos[k] for k in ("dx", "dy", "angulo")]
        gestor = GestorAsas2D(l, SimpleNamespace(campos=campos), asas, tipos)
        gestor._de_transformar, gestor._clave = True, clave
        l._asas = gestor
