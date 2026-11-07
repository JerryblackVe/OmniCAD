# -*- coding: utf-8 -*-
"""Patrón rectangular y circular del boceto con su panel (Fusion: Rectangular / Circular Pattern).

Causa raíz del video de Gerardo (2026-10-30): el cálculo de las copias era exacto; fallaba el flujo. La herramienta pedía
«elegir, Enter (sin señal en pantalla), clic en el centro y una caja flotante con cuatro valores», sin dirección libre,
sin sentido, sin excluir copias antes de aceptar y sin poder cambiar el centro después. Acá el estado vive en un
controlador y la persona lo maneja desde `ui/panel_patron.py`, desde el dibujo (clic en la geometría, el centro, la línea
de dirección, las asas y las casillas de cada copia) o con las dos cosas a la vez: todo queda sincronizado porque los campos
del panel son la única fuente de los valores y las asas escriben en ellos.

La vista previa y la creación usan el MISMO cálculo del núcleo (`Boceto.previa_patron` / `patron_*`): lo que se ve es lo
que se crea, y la vista previa no toca el boceto ni el solver. Editar un patrón ya hecho (doble clic en su glifo) abre el
mismo panel; Cancelar lo deja como estaba."""
import math
from types import SimpleNamespace

from PySide6.QtCore import QPointF, QRectF, Qt
from PySide6.QtGui import QColor, QPen

from ..restricciones import ErrorBoceto
from ..timeline.parametros import ANGULO, ESCALAR, LONGITUD, ErrorExpresion
from . import formato
from .asas_boceto import Asa2D, GestorAsas2D, _desfase_px, centro_de, polilineas_de

HERRAMIENTAS = {"patron_rectangular": "rectangular", "patron_circular": "circular"}
ETIQUETAS = {"cantidad1": "Cantidad 1", "distancia1": "Distancia 1", "angulo1": "Ángulo 1", "cantidad2": "Cantidad 2",
             "distancia2": "Distancia 2", "angulo2": "Ángulo 2", "cantidad": "Cantidad", "angulo_total": "Ángulo total",
             "centro_x": "Centro X", "centro_y": "Centro Y"}
DEFECTO = {"rectangular": {"cantidad1": "3", "distancia1": "30", "angulo1": "0", "modo": "extension",
                           "simetrico1": False, "dos": False, "cantidad2": "2", "distancia2": "20", "angulo2": "90",
                           "simetrico2": False},
           "circular": {"cantidad": "6", "angulo_total": "360", "distribucion": "completo", "centro_x": "", "centro_y": ""}}
ORDEN_CAMPOS = ("seleccion", "dir1", "dir2", "centro")
TIPOS_ASA = ["int", "long", "int", "long", "int", "ang", "ang", "ang"]       # el orden de `PanelPatron.lista_campos`


class _Mal(Exception):
    """Un campo con un valor que no sirve: `clave` es el campo que se marca en rojo."""

    def __init__(self, clave, mensaje):
        super().__init__(mensaje)
        self.clave = clave


def dibujar_casilla(p, caja, suprimida, oscuro):
    """La casilla de una copia (Fusion: se desmarca para excluir esa instancia): marcada = la copia existe."""
    p.setPen(QPen(QColor(150, 155, 165) if oscuro else QColor(110, 110, 110), 1))
    p.setBrush(QColor(58, 63, 75, 230) if oscuro else QColor(250, 250, 250, 235))
    p.drawRect(caja)
    if not suprimida:
        p.setPen(QPen(QColor(0, 180, 255), 2))
        p.drawLine(QPointF(caja.left() + 2.5, caja.center().y()), QPointF(caja.center().x() - 0.5, caja.bottom() - 3))
        p.drawLine(QPointF(caja.center().x() - 0.5, caja.bottom() - 3), QPointF(caja.right() - 2.5, caja.top() + 3))


def _angulo(v):
    return math.degrees(math.atan2(v[1], v[0]))


class ControlPatron:
    """Estado y comportamiento de las dos herramientas de patrón de un `Lienzo`."""

    def __init__(self, lienzo):
        self.l = lienzo
        self.panel = None            # lo conecta ModoBoceto
        self.tipo = None
        self.editando = None         # id del patrón que se edita, o None
        self.campo = "seleccion"     # qué llena el próximo clic: seleccion, centro, dir1 o dir2
        self.centro = None           # None, id de punto o (x, y)
        self.lineas = {"dir1": None, "dir2": None}
        self.suprimidos = set()
        self.previa = True
        self.textos = {}
        self.error_clic = ""
        self._cache = None
        self._firma = self._estado = None

    @property
    def activo(self):
        return self.tipo is not None and self.l.herramienta in HERRAMIENTAS

    # ------------------------------------------------------------ arranque y cierre
    def iniciar(self, herramienta):
        """Al elegir la herramienta (o cambiar de herramienta): estado nuevo. Con algo ya elegido salta al centro."""
        self.cerrar()
        self.tipo = HERRAMIENTAS.get(herramienta)
        if self.tipo is None:
            return
        self.textos = dict(DEFECTO[self.tipo])
        self.l.fase = self.campo = "seleccion"
        if self.l._seleccion_util() and self.tipo == "circular":
            self.l.fase = self.campo = "centro"
        self._emitir()

    def cerrar(self):
        """Suelta todo (también las asas): no queda geometría ni estado a medias."""
        if self.l._asas is not None and self.tipo is not None:
            self.l._asas.cerrar()
            self.l._asas = None
        self.tipo = self.editando = self.centro = self._cache = self._firma = self._estado = None
        self.l.copias_en_edicion = frozenset()
        self.lineas = {"dir1": None, "dir2": None}
        self.suprimidos, self.error_clic, self.previa = set(), "", True

    def cargar(self, registro):
        """Editar un patrón ya hecho: el panel arranca con sus valores. Cancelar no toca el boceto."""
        p, l = registro["params"], self.l
        self.tipo, self.editando = registro["tipo"], registro["id"]
        l.seleccion = [i for i in registro["ids"] if i in l.b.curvas or i in l.b.puntos]
        self.suprimidos, self.previa, self.error_clic = set(registro["suprimidos"]), True, ""
        # Las copias que ya existen se ocultan mientras dura el panel: la vista previa trae las nuevas y, debajo, las
        # viejas hacían difícil ver qué cambió.
        l.copias_en_edicion = frozenset(i for ids in registro["copias"].values() for i in ids)
        self.lineas = {"dir1": p.get("linea1"), "dir2": p.get("linea2")}
        if self.tipo == "rectangular":
            self.textos = {"cantidad1": str(p["cantidad1"]), "distancia1": formato.numero(p["distancia1"]),
                           "angulo1": formato.numero(_angulo(p["dir1"]), angular=True), "modo": p["modo"],
                           "simetrico1": bool(p["simetrico"]), "dos": p["cantidad2"] > 1,
                           "cantidad2": str(max(p["cantidad2"], 2)), "distancia2": formato.numero(p["distancia2"] or 20.0),
                           "angulo2": formato.numero(_angulo(p["dir2"]), angular=True),
                           "simetrico2": bool(p.get("simetrico2", p["simetrico"]))}
            self.campo = "seleccion"
        else:
            total = p["angulo_total"]
            self.centro = p["centro"] if isinstance(p["centro"], int) else tuple(p["centro"])
            self.textos = {"cantidad": str(p["cantidad"]), "angulo_total": formato.numero(total, angular=True),
                           "distribucion": "completo" if abs(abs(total) - 360.0) < 1e-9 else
                           "simetrico" if p["simetrico"] else "parcial", "centro_x": "", "centro_y": ""}
            self._texto_centro()
            self.campo = "centro"
        for clave, texto in p.get("expresiones", {}).items():
            self.textos[clave] = texto
        l.fase = self.campo
        self._cache = None
        self._emitir()

    # ------------------------------------------------------------ valores
    def recibir(self, textos):
        """Los campos del panel cambiaron (tecla, combo, casilla): se evalúa de nuevo y se repinta."""
        antes, self.textos = self.textos, dict(textos)
        t = self.textos
        if self.tipo == "circular":
            if t.get("distribucion") != antes.get("distribucion"):
                signo = "-" if str(t.get("angulo_total", "")).strip().startswith("-") else ""
                t["angulo_total"] = signo + "360" if t["distribucion"] == "completo" else (
                    t["angulo_total"] if abs(self._numero_o_none("angulo_total", ANGULO) or 360.0) != 360.0
                    else signo + "180")
            if (t.get("centro_x"), t.get("centro_y")) != (antes.get("centro_x"), antes.get("centro_y")):
                xy = [self._numero_o_none(k, LONGITUD) for k in ("centro_x", "centro_y")]
                if None not in xy:
                    self.centro = (xy[0], xy[1])
        self._emitir()
        self.l.update()

    def _numero_o_none(self, clave, tipo):
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

    def _entero(self, clave):
        v = self._numero(clave, ESCALAR)
        if abs(v - round(v)) > 1e-9:
            raise _Mal(clave, f"«{ETIQUETAS[clave]}» tiene que ser un número entero (escribiste {self.textos[clave]}).")
        return int(round(v))

    def _direccion(self, k):
        """(vector unitario, línea) de la dirección k del patrón: la línea elegida o el ángulo escrito."""
        linea = self.lineas[f"dir{k}"]
        if linea is not None:
            if linea not in self.l.b.curvas:
                raise _Mal(f"angulo{k}", f"La línea de la dirección {k} ya no existe: elegí otra.")
            a, b = self.l.b._extremos_linea(linea)
            largo = math.dist(a, b)
            if largo < 1e-9:
                raise _Mal(f"angulo{k}", f"La línea de la dirección {k} tiene largo cero.")
            return [(b[0] - a[0]) / largo, (b[1] - a[1]) / largo], linea
        a = math.radians(self._numero(f"angulo{k}", ANGULO))
        return [math.cos(a), math.sin(a)], None

    def parametros(self):
        """Los parámetros del núcleo con lo que hay en los campos, o `_Mal`. Es el mismo diccionario que guarda el patrón."""
        t = self.textos
        if self.tipo == "rectangular":
            dos = bool(t.get("dos"))
            d1, linea1 = self._direccion(1)
            d2, linea2 = self._direccion(2) if dos else ([0.0, 1.0], None)
            return {"cantidad1": self._entero("cantidad1"), "distancia1": self._numero("distancia1"),
                    "cantidad2": self._entero("cantidad2") if dos else 1,
                    "distancia2": self._numero("distancia2") if dos else 0.0, "dir1": d1, "dir2": d2,
                    "modo": t["modo"], "simetrico": bool(t.get("simetrico1")), "simetrico2": bool(t.get("simetrico2")),
                    "linea1": linea1, "linea2": linea2}
        completo = t.get("distribucion") == "completo"
        total = self._numero("angulo_total", ANGULO)
        if completo:
            total = -360.0 if total < 0 else 360.0
        if self.centro is None:
            raise _Mal("", "Elegí el centro del patrón: clic en un punto (o en el origen) del dibujo.")
        centro = self.centro
        if isinstance(centro, int):
            if centro not in self.l.b.puntos:
                raise _Mal("", "El punto del centro ya no existe: elegí otro.")
        else:
            centro = [float(centro[0]), float(centro[1])]
        return {"centro": centro, "cantidad": self._entero("cantidad"), "angulo_total": total,
                "simetrico": t.get("distribucion") == "simetrico" and not completo}

    def calcular(self):
        """{params, error, malos, polis, copias}: se rehace solo si cambió algo que importa (campos, elegido, boceto)."""
        l = self.l
        ids = l._seleccion_util()
        clave = (self.tipo, tuple(ids), tuple(sorted(self.textos.items())), self.centro, tuple(self.lineas.values()),
                 tuple(sorted(self.suprimidos)), l._generacion)
        if self._cache is not None and self._cache[0] == clave:
            return self._cache[1]
        r = {"params": None, "error": "", "malos": set(), "polis": [], "copias": 0, "falta": False}
        try:
            if not ids:
                r["falta"] = True
                raise _Mal("", "Elegí la geometría a repetir: clic en cada curva o una ventana de selección.")
            r["params"] = params = self.parametros()
            ids = [i for i in ids if i != params["centro"]] if isinstance(params.get("centro"), int) else ids
            if not ids:
                raise _Mal("", "Lo único elegido es el centro: elegí otra geometría para repetir.")
            polilineas = polilineas_de(l, ids)
            r["polis"] = [poli for copia in l.b.previa_patron(self.tipo, params, polilineas, self.suprimidos, ids)
                          for poli in copia]
            r["copias"] = (params["cantidad1"] * params["cantidad2"] if self.tipo == "rectangular"
                           else params["cantidad"]) - 1
        except _Mal as e:
            r["error"], r["malos"] = str(e), {e.clave} if e.clave else set()
            r["falta"] = r["falta"] or not e.clave
        except ErrorBoceto as e:
            r["error"] = str(e)
        self._cache = (clave, r)
        return r

    # ------------------------------------------------------------ estado para el panel
    def _texto_centro(self):
        c, b = self.centro, self.l.b
        if c is None:
            self.textos["centro_x"] = self.textos["centro_y"] = ""
            return
        x, y = b.coords(c) if isinstance(c, int) and c in b.puntos else (c if not isinstance(c, int) else (0.0, 0.0))
        self.textos["centro_x"], self.textos["centro_y"] = formato.numero(x), formato.numero(y)

    def _etiqueta_centro(self):
        c, b = self.centro, self.l.b
        if c is None:
            return ""
        if isinstance(c, int):
            return "Punto %d" % c if c in b.puntos else "Punto perdido"
        return "Origen" if math.hypot(*c) < 1e-9 else "(%s, %s)" % (formato.numero(c[0]), formato.numero(c[1]))

    def estado(self):
        """Lo que muestra el panel: conteos de cada selección, campo activo, valores, qué falta y qué reparo hay."""
        l, r = self.l, self.calcular()
        nombres = {k: ("Línea %d" % v if v is not None else "") for k, v in self.lineas.items()}
        guia = ""
        if r["falta"] and not r["error"].startswith("Elegí el centro"):
            guia = r["error"]
        elif self.campo == "centro" and self.centro is None:
            guia = "Elegí el centro: clic en un punto del dibujo o en el origen."
        elif not r["error"]:
            guia = ("Clic en la casilla de una copia para excluirla. Enter acepta y Esc cancela." if r["copias"] > 1
                    else "Enter acepta y Esc cancela.")
        error = r["error"] if not r["falta"] else ""
        if self.error_clic:
            error = self.error_clic
        return {"tipo": self.tipo, "editando": self.editando is not None, "campo": self.campo,
                "conteos": {"seleccion": len(l._seleccion_util()), "centro": int(self.centro is not None),
                            "dir1": int(self.lineas["dir1"] is not None), "dir2": int(self.lineas["dir2"] is not None)},
                "etiquetas": {"centro": self._etiqueta_centro(), "dir1": nombres["dir1"], "dir2": nombres["dir2"]},
                "campos": dict(self.textos), "malos": set(r["malos"]), "valido": r["params"] is not None and not r["error"],
                "guia": guia if not error else "", "error": error, "previa": self.previa}

    def _emitir(self):
        """Le manda el estado al panel (solo si cambió) y deja las asas listas."""
        if not self.activo or self.panel is None:
            return
        firma = (tuple(self.l._seleccion_util()), self.campo, self.centro, tuple(self.lineas.values()))
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
            self.error_clic = "Primero elegí la geometría a repetir."
        else:
            self.error_clic = ""
            self.l.fase = self.campo = campo
        self._emitir()
        self.l.update()

    def limpiar_campo(self, campo):
        """La ✕ de un campo lo vacía y lo deja listo para elegir de nuevo."""
        if campo == "seleccion":
            self.l.seleccion = []
        elif campo == "centro":
            self.centro = None
            self._texto_centro()
        else:
            self.lineas[campo] = None
        self.l.fase = self.campo = campo
        self._emitir()
        self.l.update()

    def invertir(self, clave):
        """⇄: cambia el signo del valor (la distancia al otro lado, el ángulo al otro sentido)."""
        c = self.panel.campos[{"angulo": "angulo_total"}.get(clave, clave)]
        texto = c.text().strip()
        if not texto:
            return
        simple = texto.lstrip("-").replace(",", ".").replace(".", "", 1).isdigit()      # un número: se cambia su signo
        if texto.startswith("-(") and texto.endswith(")"):
            c.setText(texto[2:-1])
        elif simple:
            c.setText(texto[1:] if texto.startswith("-") else "-" + texto)
        else:
            c.setText(f"-({texto})")                                                  # una expresión: se niega entera

    def set_previa(self, activa):
        self.previa = bool(activa)
        self._emitir()
        self.l.update()

    def clic(self, pos):
        """Clic de posición del campo activo (centro o línea de dirección). True si lo usó."""
        l = self.l
        if self.campo == "centro":
            pid, xy = l._ajustar(pos)
            self.centro = pid if pid is not None else (round(xy[0], 9), round(xy[1], 9))
            self.error_clic = ""
            self._texto_centro()
            self._emitir()
            return True
        if self.campo in ("dir1", "dir2"):
            cid = l._curva_cercana(pos, tipos=("linea",))
            if cid is None:
                self.error_clic = "Ahí no hay ninguna línea: hacé clic sobre la línea que da la dirección."
            else:
                self.lineas[self.campo] = cid
                self.error_clic = ""
                l.mensaje.emit("")
            self._emitir()
            return True
        return False

    def enter(self):
        """Enter: con todo bien acepta; con la geometría lista pasa al centro; si no, dice qué falta."""
        e = self.estado()
        if e["valido"]:
            self.aceptar()
        elif self.campo == "seleccion" and self.l._seleccion_util() and self.tipo == "circular" and self.centro is None:
            self.elegir_campo("centro")
        else:
            self.l.mensaje.emit(e["error"] or e["guia"])

    # ------------------------------------------------------------ casillas de cada copia
    def casillas(self):
        """[(índice de copia, QRectF en px, suprimida)]: una casilla junto a cada copia de la vista previa."""
        r = self.calcular()
        if not self.previa or r["params"] is None or r["error"]:
            return []
        l, p = self.l, r["params"]
        trans = l.b._trans_rectangular(p) if self.tipo == "rectangular" else l.b._trans_circular(p)[0]
        centro = centro_de(l, l._seleccion_util())
        salida = []
        for i, (fn, *_) in enumerate(trans):
            q = l.a_px(*fn(centro))
            salida.append((i, QRectF(q.x() + 6, q.y() - 18, 12, 12), i in self.suprimidos))
        return salida

    def clic_casilla(self, pos):
        for i, caja, _s in self.casillas():
            if caja.adjusted(-3, -3, 3, 3).contains(pos):
                self.suprimidos ^= {i}
                self._cache = None
                self._emitir()
                self.l.update()
                return True
        return False

    # ------------------------------------------------------------ aceptar y cancelar
    def aceptar(self):
        """Aceptar (botón, Enter o Enter en un campo): crea o edita el patrón en UN paso de deshacer y sale."""
        l, e = self.l, self.estado()
        if not e["valido"]:
            l.mensaje.emit(e["error"] or e["guia"])
            return False
        r, perdidas = self.calcular(), []
        p, ids, pid = dict(r["params"]), l._seleccion_util(), self.editando
        claves = ("distancia1", "angulo1") if self.tipo == "rectangular" else ("angulo_total",)
        if self.tipo == "rectangular" and self.textos.get("dos"):
            claves += ("distancia2", "angulo2")
        p["expresiones"] = {k: str(self.textos[k]).strip() for k in claves}
        sup = sorted(i for i in self.suprimidos if i < r["copias"])          # las de una cantidad anterior ya no existen

        def hacer():
            if pid is not None:
                perdidas.extend(l.b.editar_patron(pid, suprimidos=sup, **p))
            elif self.tipo == "rectangular":
                l.b.patron_rectangular(ids, p["cantidad1"], p["distancia1"], p["cantidad2"], p["distancia2"], p["dir1"],
                                       p["dir2"], p["modo"], p["simetrico"], p["linea1"], p["linea2"], sup, p["simetrico2"],
                                       p["expresiones"])
            else:
                l.b.patron_circular(ids, p["centro"], p["cantidad"], p["angulo_total"], p["simetrico"], sup, p["expresiones"])
        if not l.aplicar_cambio(hacer, anclar=False):
            return False
        if perdidas:
            l.mensaje.emit("Se borraron porque su copia ya no existe: " + ", ".join(perdidas))
        l.seleccion = []
        l.set_herramienta("seleccionar")
        return True

    def cancelar(self):
        """Cancelar (botón, ✕ o Esc): sale sin tocar el boceto."""
        self.l.set_herramienta("seleccionar")

    # ------------------------------------------------------------ dibujo
    def dibujar(self, p, acento):
        """Vista previa de las copias (con la casilla activa), el centro o las direcciones y las casillas de exclusión."""
        l, r = self.l, self.calcular()
        pen = QPen(QColor(255, 140, 0), 1, Qt.DashDotLine)
        c0 = centro_de(l, l._seleccion_util())
        if self.tipo == "circular" and self.centro is not None:
            o = l.b.coords(self.centro) if isinstance(self.centro, int) and self.centro in l.b.puntos else (
                self.centro if not isinstance(self.centro, int) else None)
            if o is not None:
                q = l.a_px(*o)
                p.setPen(QPen(QColor(255, 140, 0), 2))
                p.drawEllipse(q, 7, 7)
                p.drawLine(QPointF(q.x() - 11, q.y()), QPointF(q.x() + 11, q.y()))
                p.drawLine(QPointF(q.x(), q.y() - 11), QPointF(q.x(), q.y() + 11))
                if math.dist(o, c0) > 1e-9:
                    p.setPen(pen)
                    p.drawLine(q, l.a_px(*c0))
        elif self.tipo == "rectangular" and r["params"] is not None:
            for k in (1, 2):
                v = r["params"][f"dir{k}"]
                if k == 2 and r["params"]["cantidad2"] < 2:
                    continue
                largo = 40.0 / max(l.px_por_mm(), 1e-9)
                p.setPen(pen)
                p.drawLine(l.a_px(*c0), l.a_px(c0[0] + v[0] * largo, c0[1] + v[1] * largo))
        for k in ("dir1", "dir2"):
            cid = self.lineas[k]
            if cid in l.b.curvas and self.tipo == "rectangular":
                a, b = (l.a_px(*q) for q in l.b._extremos_linea(cid))
                p.setPen(QPen(QColor(255, 140, 0), 3))
                p.drawLine(a, b)
        if self.previa and r["polis"]:
            p.setPen(QPen(acento, 2.0))
            for poli in r["polis"]:
                l._dibujar_polilinea(p, poli)
        p.save()
        for _i, caja, suprimida in self.casillas():
            dibujar_casilla(p, caja, suprimida, l._oscuro())
        p.restore()

    # ------------------------------------------------------------ asas
    def _armar_asas(self):
        """Las asas de la vista (distancia y cantidad por dirección; ángulo y cantidad en el circular), atadas a los campos
        del panel. Se rehacen solo si cambió el tipo o la geometría elegida."""
        l = self.l
        r = self.calcular() if self.activo else None
        if r is None or r["params"] is None or self.panel is None:       # un valor que el núcleo rechaza (ángulo 0) deja las asas
            if l._asas is not None and getattr(l._asas, "_de_patron", False):
                l._asas.cerrar()
                l._asas = None
            return
        if l._asas is not None and not getattr(l._asas, "_de_patron", False):
            return                                        # otra herramienta con sus propias asas
        p = r["params"]
        # La dirección de una fila sin línea la mueve su asa de ángulo: no entra en la clave, o soltar el asa a la mitad
        # de un arrastre rearmaría todas. Con una línea de dirección, sí (es fija).
        direcciones = tuple(round(x, 9) for k in (1, 2) if self.lineas[f"dir{k}"] is not None for x in p.get(f"dir{k}", ()))
        clave = (self.tipo, tuple(l._seleccion_util()), self.centro, direcciones, p.get("modo"), p["cantidad2"] > 1
                 if self.tipo == "rectangular" else p["angulo_total"] > 0)
        if l._asas is not None and getattr(l._asas, "_clave", None) == clave:
            return
        if l._asas is not None:
            l._asas.cerrar()
        asas = self._asas_rectangular(r["params"]) if self.tipo == "rectangular" else self._asas_circular(r["params"])
        gestor = GestorAsas2D(l, SimpleNamespace(campos=self.panel.lista_campos), asas, TIPOS_ASA)
        gestor._de_patron, gestor._clave = True, clave
        l._asas = gestor

    def _asas_rectangular(self, p):
        l = self.l
        c = centro_de(l, l._seleccion_util())
        extension = p["modo"] == "extension"

        def eje(dirk, i_n, i_d, i_a, lado):
            linea = self.lineas[f"dir{dirk}"] is not None
            fija = p[f"dir{dirk}"]

            def u(v):                       # la fila sigue el ángulo escrito; con una línea de dirección, la de la línea
                return fija if linea else (math.cos(math.radians(v[i_a])), math.sin(math.radians(v[i_a])))

            def largo(v):
                n = max(int(v[i_n]), 1)
                return v[i_d] if extension else v[i_d] * (n - 1 if n > 1 else 1)

            def donde(v, lateral=0.0):
                e, d = largo(v), u(v)
                return (c[0] + d[0] * e - d[1] * lateral * lado, c[1] + d[1] * e + d[0] * lateral * lado)

            def dist(xy, v, v0=None, xy0=None):
                d = u(v)
                t = (xy[0] - c[0]) * d[0] + (xy[1] - c[1]) * d[1]
                n = int(v[i_n])
                return t if extension or n <= 1 else t / (n - 1)

            def cantidad(xy, v, v0=None, xy0=None):
                n0, d = int(v0[i_n]), u(v0)
                paso = (v0[i_d] / (n0 - 1) if extension and n0 > 1 else v0[i_d]) or 10.0
                t = (xy[0] - xy0[0]) * d[0] + (xy[1] - xy0[1]) * d[1]
                return n0 + round(t / paso)

            def angulo(xy, v, v0=None, xy0=None):
                giro = _angulo((xy[0] - c[0], xy[1] - c[1]))
                return giro + 360.0 * round((v[i_a] - giro) / 360.0)          # sin saltos de vuelta al cruzar ±180°
            asas = [Asa2D(i_d, donde, dist, ancla=lambda v: c, ayuda="Distancia"),
                    Asa2D(i_n, lambda v: donde(v, _desfase_px(l)), cantidad, tipo="int", minimo=1, maximo=200,
                          ayuda="Cantidad")]
            giro = None
            if not linea:                   # BOC-62: un asa a 56 px del centro que gira la dirección
                radio = 56.0 / max(l.px_por_mm(), 1e-9)
                giro = Asa2D(i_a, lambda v: (c[0] + radio * u(v)[0], c[1] + radio * u(v)[1]), angulo, ancla=lambda v: c,
                             tipo="ang", ayuda="Ángulo")
            return asas, giro
        asas, giros = [], []
        for dirk, i_n, i_d, i_a, lado in ((1, 0, 1, 6, 1.0), (2, 2, 3, 7, -1.0)):
            if dirk == 2 and not (p["cantidad2"] > 1 or self.textos.get("dos")):
                continue
            nuevas, giro = eje(dirk, i_n, i_d, i_a, lado)
            asas += nuevas
            giros += [giro] if giro is not None else []
        return asas + giros                  # los giros al final: los índices de las asas de distancia y cantidad no cambian

    def _asas_circular(self, p):
        l = self.l
        o = l.b.coords(p["centro"]) if isinstance(p["centro"], int) else (float(p["centro"][0]), float(p["centro"][1]))
        ids = [i for i in l._seleccion_util() if i != p["centro"]]
        c = centro_de(l, ids)
        radio = math.dist(c, o) or 25.0
        a0 = _angulo((c[0] - o[0], c[1] - o[1])) if math.dist(c, o) > 1e-9 else 0.0

        def en(grados, r=radio):
            a = math.radians(a0 + grados)
            return (o[0] + r * math.cos(a), o[1] + r * math.sin(a))

        def paso_deg(v):
            n, total = max(int(v[4]), 1), v[5]
            return total / n if abs(abs(total) - 360.0) < 1e-9 else (total / (n - 1) if n > 1 else total)

        def desenvolver(grados, ref):
            return grados + 360.0 * round((ref - grados) / 360.0)

        def total(xy, v, v0=None, xy0=None):
            t = desenvolver(_angulo((xy[0] - o[0], xy[1] - o[1])) - a0, v[5])
            return 360.0 if abs(t - 360.0) < 3.0 else (-360.0 if abs(t + 360.0) < 3.0 else t)

        def cantidad(xy, v, v0=None, xy0=None):
            paso = paso_deg(v0) or 30.0
            giro = desenvolver(_angulo((xy[0] - o[0], xy[1] - o[1])) - _angulo((xy0[0] - o[0], xy0[1] - o[1])), 0.0)
            return max(int(v0[4]), 1) + round(giro / paso)
        return [Asa2D(5, lambda v: en(v[5]), total, ancla=lambda v: o, tipo="ang", minimo=-360.0, maximo=360.0,
                      ayuda="Ángulo total"),
                Asa2D(4, lambda v: en(paso_deg(v) * (max(int(v[4]), 1) - 1), radio + _desfase_px(l)), cantidad,
                      tipo="int", minimo=2, maximo=200, ayuda="Cantidad")]
