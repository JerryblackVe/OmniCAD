# -*- coding: utf-8 -*-
"""
Diálogos de comando al estilo de Fusion 360.

En Fusion cada comando (Extruir, Empalme, Agujero…) abre un panel flotante sobre el lienzo con
filas de SELECCIÓN ("Seleccionar" → se elige en la vista 3D), medidas con expresiones, listas de
opciones y casillas; el modelo muestra una VISTA PREVIA en vivo y Aceptar agrega el paso al
timeline. Acá:
  - `Comando` describe un comando de forma declarativa: sus campos, cómo arma la operación del
    timeline (`construir`) y cómo leer una operación existente para editarla (`desde_op`).
  - `PanelComando` es el panel: arma los widgets, maneja la selección en el visor (filtros,
    resalte, avance automático al siguiente campo) y pide la vista previa al documento.
Las selecciones se guardan como referencias serializables (`timeline.entidades`), así la
operación sigue apuntando a "su" cara o arista al recalcular.
"""
from PySide6.QtCore import QSize, Qt, QTimer, Signal
from PySide6.QtWidgets import (QCheckBox, QComboBox, QFrame, QGridLayout, QHBoxLayout, QLabel, QLayout, QLineEdit,
                               QPushButton, QSpinBox, QToolButton, QVBoxLayout, QWidget)

from ..timeline.parametros import ANGULO, ESCALAR, LONGITUD, ErrorExpresion
from . import temas
from .iconos import icono


class ErrorComando(ValueError):
    """Faltan datos para armar la operación (se muestra en el panel, no es un error del modelo)."""


# ---------------------------------------------------------------- campos
class Campo:
    def __init__(self, clave, etiqueta, defecto=None, visible_si=None, ayuda=""):
        self.clave, self.etiqueta, self.defecto, self.visible_si, self.ayuda = clave, etiqueta, defecto, visible_si, ayuda


class Seleccion(Campo):
    """Fila "Seleccionar": `filtros` es un subconjunto de visor3d.FILTROS; maximo=None = sin límite."""

    def __init__(self, clave, etiqueta, filtros, minimo=1, maximo=1, **kw):
        super().__init__(clave, etiqueta, [], **kw)
        self.filtros, self.minimo, self.maximo = set(filtros), minimo, maximo


class Expresion(Campo):
    def __init__(self, clave, etiqueta, defecto="10 mm", tipo=LONGITUD, **kw):
        super().__init__(clave, etiqueta, defecto, **kw)
        self.tipo = tipo


class Opciones(Campo):
    """Lista desplegable. `opciones`: dict clave → texto (o (texto, ícono))."""

    def __init__(self, clave, etiqueta, opciones, defecto=None, **kw):
        super().__init__(clave, etiqueta, defecto if defecto is not None else next(iter(opciones)), **kw)
        self.opciones = opciones


class Casilla(Campo):
    def __init__(self, clave, etiqueta, defecto=False, **kw):
        super().__init__(clave, etiqueta, defecto, **kw)


class Entero(Campo):
    def __init__(self, clave, etiqueta, defecto=1, minimo=1, maximo=10000, **kw):
        super().__init__(clave, etiqueta, defecto, **kw)
        self.minimo, self.maximo = minimo, maximo


class Texto(Campo):
    def __init__(self, clave, etiqueta, defecto="", **kw):
        super().__init__(clave, etiqueta, defecto, **kw)


class Info(Campo):
    """Texto de solo lectura calculado con `funcion(valores, ctx) -> str` (resultados de medir…)."""

    def __init__(self, clave, etiqueta, funcion, **kw):
        super().__init__(clave, etiqueta, None, **kw)
        self.funcion = funcion


# ---------------------------------------------------------------- contexto y comando
class ContextoComando:
    """Lo que un comando necesita saber: el documento, la ventana, la operación que se edita (o None)
    y el estado del modelo ANTES del paso (como Fusion al editar una feature)."""

    def __init__(self, doc, ventana=None, op=None):
        self.doc, self.ventana, self.op = doc, ventana, op
        self.indice = doc.indice(op.id) if op is not None else doc.marcador
        self.estado = doc.estado_en(self.indice)
        self.parametros = doc.parametros

    def evaluar(self, expr, tipo=LONGITUD):
        return self.parametros.evaluar(expr, tipo)

    def nuevo_id(self):
        return self.op.id if self.op is not None else self.doc.nuevo_id()


class Comando:
    CLAVE = ""
    TITULO = ""
    ICONO = ""
    CLASE_OP = None          # para editar: la ventana busca el comando por el TIPO de la operación
    PREVIA = True            # mostrar la vista previa del resultado
    TEXTO_ACEPTAR = "Aceptar"
    SIN_OP = False           # comandos que no agregan un paso al timeline (aspecto, medir…): usan `aplicar`

    def campos(self, ctx):
        return []

    def verificar(self, ctx):
        """Mensaje si el comando no se puede usar ahora (p. ej. no hay cuerpos); None si se puede."""
        return None

    def construir(self, v, ctx):
        raise NotImplementedError

    def desde_op(self, op, ctx):
        return dict(op.p)

    def nombre_nuevo(self, ctx):
        """Nombre del paso nuevo como en Fusion: Empalme1, Empalme2…"""
        base = self.TITULO.split(" ")[0] if self.CLASE_OP is None else self.CLASE_OP.ETIQUETA.split(" ")[0]
        usados = {o.nombre for o in ctx.doc.operaciones}
        n = 1
        while f"{base}{n}" in usados:
            n += 1
        return f"{base}{n}"

    def crear_op(self, clase, v, ctx, **params):
        """Arma la operación nueva o la versión editada (conserva id, nombre y supresión)."""
        if ctx.op is not None:
            return clase(ctx.op.id, ctx.op.nombre, ctx.op.suprimida, **params)
        return clase(ctx.doc.nuevo_id(), self.nombre_nuevo(ctx), **params)

    def al_cerrar(self, ctx):
        """Limpieza al cerrar el panel (capas de análisis, colores…)."""

    def aplicar(self, v, ctx):
        """Para los comandos SIN_OP: lo que hace Aceptar."""

    def mostrar(self, v, ctx):
        """Para los comandos SIN_OP: lo que se ve en la vista mientras el diálogo está abierto."""

    def ajustar_hit(self, campo, hit, ctx, visor):
        """Gancho al elegir algo en la vista: puede devolver el hit corregido (p. ej. enganchado al centro de la
        cara). None = sin cambios."""
        return None

    def manipuladores(self, ctx, v):
        """Manipuladores en la vista (`ui/manipuladores.py`: Flecha, Angulo, Triada…) para los valores `v`.
        El panel los recalcula cada vez que cambia un valor; [] = sin manipuladores."""
        return []

    def previa_vista(self, ctx, v, op):
        """Dibujo extra de la vista previa ([primitivas] de `visor.set_capa`), p. ej. el agujero en rojo.
        Se calcula junto con la vista previa del modelo (no en cada movimiento del ratón)."""
        return None


def hit_desde_ref(ref, estado):
    """Selección (como la que arma el visor al hacer clic) a partir de una referencia guardada: sirve
    para mostrar lo elegido al editar una operación y para la preselección."""
    import numpy as np

    from ..nucleo import geometria as geo
    from ..timeline import entidades as ent
    from .visor3d import _segmentos, teselar_cuerpo
    hit = {"ref": ref, "tipo": ref.get("tipo"), "dibujo": []}
    try:
        e = ent.resolver(ref, estado)
    except Exception:  # noqa: BLE001 — la referencia perdida se muestra igual (sin resalte)
        return hit
    hit.update(forma=e.forma, cuerpo=e.cuerpo, plano=e.plano)
    try:
        if e.tipo == "cuerpo":
            hit["dibujo"] = [("tris", teselar_cuerpo(e.forma, 0.1)[0], None, 0.35)]
        elif e.tipo in ("cara", "perfil") and e.forma is not None:
            hit["dibujo"] = [("tris", geo.teselar(e.forma)[0], None, 0.45)]
        elif e.tipo in ("arista", "curva_boceto") and e.forma is not None:
            hit["dibujo"] = [("lineas", _segmentos([geo.polilinea_arista(e.forma)]), None, 3.5)]
        elif e.punto is not None:
            hit["dibujo"] = [("puntos", np.array([e.punto], float), None, 9)]
        elif e.tipo == "eje":
            p, d = e.eje
            hit["dibujo"] = [("lineas", np.array([p - d * 60, p + d * 60]), None, 3.5)]
        elif e.tipo == "plano":
            pl, L = e.plano, 40.0
            q = [pl.a_3d(-L, -L), pl.a_3d(L, -L), pl.a_3d(L, L), pl.a_3d(-L, L)]
            hit["dibujo"] = [("tris", np.array([q[0], q[1], q[2], q[0], q[2], q[3]]), None, 0.35)]
    except Exception:  # noqa: BLE001
        pass
    return hit


def _con_forma(hit, estado):
    """La selección con su forma OCC (los perfiles que elige el visor no la traen): para las medidas."""
    if hit.get("forma") is not None or hit.get("tipo") not in ("perfil", "cara", "arista", "curva_boceto"):
        return hit
    from ..timeline import entidades as ent
    try:
        return dict(hit, forma=ent.resolver(hit["ref"], estado).forma)
    except Exception:  # noqa: BLE001
        return hit


def hits(refs_lista, estado):
    return [hit_desde_ref(r, estado) for r in (refs_lista or []) if r]


def acepta(filtros, hit):
    """¿La selección `hit` sirve para un campo con estos filtros? (misma regla que el visor)."""
    t, ref = hit.get("tipo"), hit.get("ref") or {}
    geom = (ref.get("firma") or {}).get("geom")
    if t == "cara":
        return "cara" in filtros or (bool(filtros & {"cara_plana", "plano"}) and hit.get("plano") is not None) or \
            ("eje" in filtros and geom in ("cilindro", "cono"))
    if t == "arista":
        return "arista" in filtros or (bool(filtros & {"arista_lineal", "eje"}) and geom == "linea") or \
            ("arista_circular" in filtros and geom == "circulo")
    if t == "vertice":
        return bool(filtros & {"vertice", "punto"})
    if t == "punto_boceto":
        return "punto" in filtros or "punto_boceto" in filtros
    if t == "curva_boceto":
        return "curva_boceto" in filtros or "eje" in filtros
    return t in filtros


def preseleccion(campos, seleccion):
    """Reparte lo que el usuario ya tenía elegido entre los campos de selección del comando, en orden
    (en Fusion, elegir primero y llamar al comando después llena sus selecciones)."""
    valores, restantes = {}, list(seleccion or [])
    for c in campos:
        if not isinstance(c, Seleccion) or not restantes:
            continue
        compatibles = [h for h in restantes if acepta(c.filtros, h)]
        if c.maximo is not None:
            compatibles = compatibles[:c.maximo]
        if compatibles:
            valores[c.clave] = compatibles
            restantes = [h for h in restantes if all(h is not x for x in compatibles)]
    return valores


def refs(v, clave):
    """Referencias de un campo de selección (lista de dicts)."""
    return [h["ref"] for h in v.get(clave, [])]


def ref1(v, clave):
    lista = refs(v, clave)
    return lista[0] if lista else None


def exigir(v, clave, texto):
    if not v.get(clave):
        raise ErrorComando(texto)
    return v[clave]


# ---------------------------------------------------------------- widgets
class _FilaSeleccion(QWidget):
    activar = Signal(object)
    limpiar = Signal(object)

    def __init__(self, campo, parent=None):
        super().__init__(parent)
        self.campo = campo
        h = QHBoxLayout(self)
        h.setContentsMargins(0, 0, 0, 0)
        h.setSpacing(2)
        self.boton = QPushButton(objectName="seleccion_cmd")
        self.boton.setIcon(icono("seleccionar"))
        self.boton.setIconSize(QSize(14, 14))
        self.boton.setCursor(Qt.PointingHandCursor)
        self.boton.clicked.connect(lambda: self.activar.emit(self))
        self.borrar = QToolButton(text="✕")
        self.borrar.setToolTip("Borrar la selección")
        self.borrar.clicked.connect(lambda: self.limpiar.emit(self))
        h.addWidget(self.boton, 1)
        h.addWidget(self.borrar)
        self.set_estado(0, False)

    def set_estado(self, n, activa):
        self.boton.setText("Seleccionar" if n == 0 else (f"{n} seleccionado" if n == 1 else f"{n} seleccionados"))
        self.boton.setProperty("activa", activa)
        self.boton.setProperty("lleno", n > 0)
        self.boton.style().unpolish(self.boton)
        self.boton.style().polish(self.boton)
        self.borrar.setVisible(n > 0)


class PanelComando(QFrame):
    """Panel flotante de un comando. Emite `aceptado(op)` o `cancelado()`."""
    aceptado = Signal(object)
    cancelado = Signal()
    previa = Signal(object)          # estado del modelo para mostrar (o None = volver al normal)

    def __init__(self, comando, ctx, visor, valores=None, parent=None):
        super().__init__(parent)
        self.setObjectName("panel_comando")
        self.setAttribute(Qt.WA_StyledBackground, True)
        self.comando, self.ctx, self.visor = comando, ctx, visor
        self.campos = comando.campos(ctx)
        self.valores = {c.clave: (list(c.defecto) if isinstance(c.defecto, list) else c.defecto) for c in self.campos}
        if ctx.op is not None:
            self.valores.update(comando.desde_op(ctx.op, ctx))
        if valores:
            self.valores.update(valores)
        self.widgets, self.etiquetas, self.filas_sel = {}, {}, {}
        self.activa = None
        self.ultima_op = None
        self._previa_ok = False

        v = QVBoxLayout(self)
        v.setContentsMargins(0, 0, 0, 0)
        v.setSpacing(0)
        v.setSizeConstraint(QLayout.SetFixedSize)
        cab = QFrame(objectName="cabecera_comando")
        hc = QHBoxLayout(cab)
        hc.setContentsMargins(8, 4, 4, 4)
        ico = QLabel()
        ico.setPixmap(icono(comando.ICONO).pixmap(18, 18))
        hc.addWidget(ico)
        titulo = QLabel(comando.TITULO.upper() if ctx.op is None else f"EDITAR {comando.TITULO.upper()}",
                        objectName="titulo_comando")
        hc.addWidget(titulo, 1)
        cerrar = QToolButton(text="✕")
        cerrar.clicked.connect(self.cancelar)
        hc.addWidget(cerrar)
        v.addWidget(cab)

        cuerpo = QWidget()
        self.grilla = QGridLayout(cuerpo)
        self.grilla.setContentsMargins(10, 8, 10, 6)
        self.grilla.setHorizontalSpacing(10)
        self.grilla.setVerticalSpacing(5)
        self.grilla.setColumnMinimumWidth(1, 170)
        for fila, campo in enumerate(self.campos):
            et = QLabel(campo.etiqueta, objectName="etiqueta_cmd")
            if campo.ayuda:
                et.setToolTip(campo.ayuda)
            w = self._widget(campo)
            self.grilla.addWidget(et, fila, 0)
            self.grilla.addWidget(w, fila, 1)
            self.etiquetas[campo.clave], self.widgets[campo.clave] = et, w
        v.addWidget(cuerpo)

        self.mensaje = QLabel(objectName="mensaje_comando", wordWrap=True)
        self.mensaje.setContentsMargins(10, 0, 10, 4)
        self.mensaje.setMaximumWidth(330)
        self.mensaje.hide()
        v.addWidget(self.mensaje)
        pie = QHBoxLayout()
        pie.setContentsMargins(10, 4, 10, 8)
        pie.addStretch(1)
        self.boton_ok = QPushButton(comando.TEXTO_ACEPTAR, objectName="boton_primario")
        self.boton_ok.clicked.connect(self.aceptar)
        cancelar = QPushButton("Cancelar")
        cancelar.clicked.connect(self.cancelar)
        pie.addWidget(self.boton_ok)
        pie.addWidget(cancelar)
        v.addLayout(pie)

        self._t_previa = QTimer(self, singleShot=True, interval=220)
        self._t_previa.timeout.connect(self._calcular_previa)
        self.manipuladores = None            # GestorManipuladores si el comando tiene asas en la vista
        if (type(comando).manipuladores is not Comando.manipuladores
                or type(comando).previa_vista is not Comando.previa_vista):
            from .manipuladores import GestorManipuladores
            self.manipuladores = GestorManipuladores(self)
        self.visor.entidad_elegida.connect(self._elegida)
        self._actualizar_visibles()
        self._refrescar_seleccion()
        primera = next((c for c in self.campos if isinstance(c, Seleccion) and self._visible(c)
                        and not self.valores.get(c.clave)), None)
        self._activar(primera)
        self._programar()

    # ------------------------------------------------------------ armado
    def _widget(self, campo):
        val = self.valores.get(campo.clave)
        if isinstance(campo, Seleccion):
            w = _FilaSeleccion(campo)
            w.activar.connect(lambda f: self._activar(f.campo))
            w.limpiar.connect(lambda f: self._limpiar(f.campo))
            self.filas_sel[campo.clave] = w
            return w
        if isinstance(campo, Expresion):
            w = QLineEdit(str(val))
            w.textChanged.connect(lambda t, c=campo: self._cambiar(c.clave, t.strip()))
            return w
        if isinstance(campo, Opciones):
            w = QComboBox()
            for k, texto in campo.opciones.items():
                if isinstance(texto, tuple):
                    w.addItem(icono(texto[1]), texto[0], k)
                else:
                    w.addItem(texto, k)
            i = w.findData(val)
            w.setCurrentIndex(max(i, 0))
            w.currentIndexChanged.connect(lambda _i, c=campo, w=w: self._cambiar(c.clave, w.currentData()))
            return w
        if isinstance(campo, Casilla):
            w = QCheckBox()
            w.setChecked(bool(val))
            w.toggled.connect(lambda b, c=campo: self._cambiar(c.clave, b))
            return w
        if isinstance(campo, Entero):
            w = QSpinBox(minimum=campo.minimo, maximum=campo.maximo)
            w.setValue(int(val))
            w.valueChanged.connect(lambda n, c=campo: self._cambiar(c.clave, n))
            return w
        if isinstance(campo, Texto):
            w = QLineEdit(str(val or ""))
            w.textChanged.connect(lambda t, c=campo: self._cambiar(c.clave, t))
            return w
        if isinstance(campo, Info):
            w = QLabel(wordWrap=True)
            w.setMaximumWidth(220)
            w.setTextInteractionFlags(Qt.TextSelectableByMouse)
            return w
        raise TypeError(campo)

    # ------------------------------------------------------------ valores
    def _visible(self, campo):
        return campo.visible_si is None or bool(campo.visible_si(self.valores))

    def _actualizar_visibles(self):
        for c in self.campos:
            vis = self._visible(c)
            self.widgets[c.clave].setVisible(vis)
            self.etiquetas[c.clave].setVisible(vis)
        self._validar_expresiones()

    def _validar_expresiones(self):
        for c in self.campos:
            if isinstance(c, Expresion) and self._visible(c):
                w = self.widgets[c.clave]
                try:
                    val = self.ctx.evaluar(w.text(), c.tipo)
                    unidad = "°" if c.tipo == ANGULO else ("" if c.tipo == ESCALAR else " mm")
                    w.setToolTip(f"= {val:.4g}{unidad}")
                    w.setStyleSheet("")
                except ErrorExpresion as e:
                    w.setToolTip(str(e))
                    w.setStyleSheet(f"background: {temas.color('campo_error')};")

    def _cambiar(self, clave, valor):
        self.valores[clave] = valor
        self._actualizar_visibles()
        self._programar()

    def set_valor(self, clave, valor):
        """Cambia un valor desde afuera (pruebas, manipuladores) y actualiza su widget."""
        w = self.widgets.get(clave)
        campo = next(c for c in self.campos if c.clave == clave)
        if isinstance(campo, Seleccion):
            self.valores[clave] = list(valor)
            self._refrescar_seleccion()
        elif isinstance(w, QLineEdit):
            w.setText(str(valor))
        elif isinstance(w, QComboBox):
            w.setCurrentIndex(max(w.findData(valor), 0))
        elif isinstance(w, QCheckBox):
            w.setChecked(bool(valor))
        elif isinstance(w, QSpinBox):
            w.setValue(int(valor))
        self.valores[clave] = valor if not isinstance(campo, Seleccion) else list(valor)
        self._actualizar_visibles()
        self._programar()

    # ------------------------------------------------------------ selección en la vista
    def _activar(self, campo):
        self.activa = campo
        for clave, fila in self.filas_sel.items():
            fila.set_estado(len(self.valores.get(clave) or []), campo is not None and clave == campo.clave)
        self.visor.set_filtro(campo.filtros if campo is not None else None)

    def _limpiar(self, campo):
        self.valores[campo.clave] = []
        self._refrescar_seleccion()
        self._activar(campo)
        self._programar()

    def _elegida(self, hit):
        campo = self.activa
        if campo is None or not self.isVisible():
            return
        try:
            hit = self.comando.ajustar_hit(campo, hit, self.ctx, self.visor) or hit
        except Exception:  # noqa: BLE001 — sin el ajuste, vale lo que se tocó
            pass
        lista = list(self.valores.get(campo.clave) or [])
        repetida = next((h for h in lista if h["ref"] == hit["ref"]), None)
        if repetida is not None:            # clic sobre algo ya elegido: se quita (como Fusion)
            lista.remove(repetida)
        elif campo.maximo == 1:
            lista = [hit]
        elif campo.maximo is None or len(lista) < campo.maximo:
            lista.append(hit)
        self.valores[campo.clave] = lista
        self._refrescar_seleccion()
        if campo.maximo is not None and len(lista) >= campo.maximo:
            siguiente = self._siguiente_seleccion(campo)
            self._activar(siguiente if siguiente is not None else campo)
        else:
            self._activar(campo)
        self._actualizar_visibles()
        self._programar()

    def _siguiente_seleccion(self, campo):
        sels = [c for c in self.campos if isinstance(c, Seleccion) and self._visible(c)]
        if campo not in sels:
            return None
        for c in sels[sels.index(campo) + 1:]:
            if not self.valores.get(c.clave):
                return c
        return None

    def _refrescar_seleccion(self):
        prims = []
        for c in self.campos:
            if isinstance(c, Seleccion):
                for h in self.valores.get(c.clave) or []:
                    prims.extend(h.get("dibujo") or [])
        self.visor.set_capa("seleccion", prims)
        for clave, fila in self.filas_sel.items():
            fila.set_estado(len(self.valores.get(clave) or []), self.activa is not None and clave == self.activa.clave)
        self._informar_medidas()

    def _informar_medidas(self):
        """Medidas de lo elegido abajo a la derecha, como Fusion ("1 Perfil | Área: 1341.141 mm^2")."""
        info = getattr(self.ctx.ventana, "info_seleccion", None)
        if info is None:
            return
        lista = [h for c in self.campos if isinstance(c, Seleccion) and self._visible(c)
                 for h in self.valores.get(c.clave) or []]
        try:
            from .medidas import texto_medidas
            texto = texto_medidas([_con_forma(h, self.ctx.estado) for h in lista], self.ctx.estado)
        except Exception:  # noqa: BLE001 — una medida que no se puede calcular no rompe el comando
            texto = ""
        info(texto)

    # ------------------------------------------------------------ vista previa
    def _programar(self):
        gestor = self.manipuladores
        if gestor is not None and gestor.arrastrando and self._t_previa.isActive():
            pass                             # arrastrando un asa: la vista previa se recalcula cada 220 ms
        else:
            self._t_previa.start()
        if gestor is not None:
            gestor.actualizar()

    def valores_visibles(self):
        return {c.clave: self.valores.get(c.clave) for c in self.campos if self._visible(c)} | {
            k: v for k, v in self.valores.items() if k not in {c.clave for c in self.campos}}

    def _calcular_previa(self):
        for c in self.campos:
            if isinstance(c, Info):
                try:
                    self.widgets[c.clave].setText(c.funcion(self.valores, self.ctx) or "")
                except Exception as e:  # noqa: BLE001 — un análisis que falla se informa en el panel
                    self.widgets[c.clave].setText(f"⚠ {e}")
        self._previa_ok = False
        if self.comando.SIN_OP:
            try:
                self.comando.mostrar(self.valores, self.ctx)
                self._mostrar("")
            except (ErrorComando, ErrorExpresion) as e:
                self._mostrar(str(e), aviso=True)
            except Exception as e:  # noqa: BLE001 — el análisis que falla se informa, no tumba la app
                self._mostrar(f"⚠ {e}")
            self._previa_ok = True
            return
        try:
            op = self.comando.construir(self.valores, self.ctx)
        except (ErrorComando, ErrorExpresion) as e:
            self.ultima_op = None
            self._mostrar(str(e), aviso=True)
            self._previa_vista(None)
            self.previa.emit(None)
            return
        self.ultima_op = op
        if op is None or not self.comando.PREVIA:
            self._mostrar("")
            self._previa_ok = True
            return
        try:
            estado, avisos = self.ctx.doc.previsualizar(op, self.ctx.indice)
        except Exception as e:  # noqa: BLE001 — se muestra el error del kernel como en Fusion
            self._mostrar(f"⚠ {e}")
            self._previa_vista(None)
            self.previa.emit(None)
            return
        self._previa_ok = True
        self._mostrar(" ".join(avisos), aviso=True)
        self._previa_vista(op)
        self.previa.emit(estado)

    def _previa_vista(self, op):
        """Dibujo extra del comando para la vista previa (el agujero en rojo…)."""
        if self.manipuladores is None:
            return
        prims = None
        if op is not None:
            try:
                prims = self.comando.previa_vista(self.ctx, self.valores, op)
            except Exception:  # noqa: BLE001 — sin el dibujo extra la vista previa sigue sirviendo
                prims = None
        self.manipuladores.mostrar_previa(prims)

    def _mostrar(self, texto, aviso=False):
        self.mensaje.setObjectName("aviso_comando" if aviso else "mensaje_comando")
        self.mensaje.setStyleSheet(f"color: {temas.color('aviso' if aviso else 'error')};")
        self.mensaje.setText(texto)
        self.mensaje.setVisible(bool(texto))
        self.adjustSize()

    # ------------------------------------------------------------ cierre
    def aceptar(self):
        if self._t_previa.isActive():
            self._t_previa.stop()
            self._calcular_previa()
        if self.comando.SIN_OP:
            try:
                self.comando.aplicar(self.valores, self.ctx)
            except (ErrorComando, ErrorExpresion) as e:
                self._mostrar(str(e), aviso=True)
                return
            self._cerrar()
            self.aceptado.emit(None)
            return
        if self.ultima_op is None:
            if not self.mensaje.text():
                self._mostrar("Faltan datos.", aviso=True)
            return
        if self.comando.PREVIA and not self._previa_ok:
            return                           # la operación falla: el mensaje rojo ya lo dice
        op = self.ultima_op
        self._cerrar()
        self.aceptado.emit(op)

    def cancelar(self):
        self._cerrar()
        self.cancelado.emit()

    def _cerrar(self):
        self._t_previa.stop()
        try:
            self.visor.entidad_elegida.disconnect(self._elegida)
        except (RuntimeError, TypeError):
            pass
        self.visor.set_filtro(None)
        self.visor.set_capa("seleccion", None)
        if self.manipuladores is not None:
            self.manipuladores.cerrar()
        info = getattr(self.ctx.ventana, "info_seleccion", None)
        if info is not None:
            info("")
        self.comando.al_cerrar(self.ctx)
        self.previa.emit(None)
        self.hide()

    def keyPressEvent(self, e):
        if e.key() in (Qt.Key_Return, Qt.Key_Enter):
            self.aceptar()
        elif e.key() == Qt.Key_Escape:
            self.cancelar()
        else:
            super().keyPressEvent(e)
