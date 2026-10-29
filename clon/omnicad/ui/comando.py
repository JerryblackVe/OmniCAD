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
import time

from PySide6.QtCore import QSize, Qt, QTimer, Signal
from PySide6.QtWidgets import (QCheckBox, QComboBox, QFrame, QGridLayout, QHBoxLayout, QLabel, QLayout, QLineEdit,
                               QPushButton, QScrollArea, QSlider, QSpinBox, QToolButton, QVBoxLayout, QWidget)

from ..timeline.documento import ErrorDocumento
from ..timeline.parametros import ANGULO, ESCALAR, LONGITUD, ErrorExpresion
from .. import registro_uso
from ..registro_uso.ganchos import error as registrar_error
from . import formato, preajustes_ui, temas
from .iconos import icono


# Vista previa «lo último gana» (P-41): cuánto se espera antes del próximo cálculo sigue a lo que costó el último.
PREVIA_CUADRO_MS, PREVIA_ESPERA_MAX_MS = 12, 220
# Operaciones cuya previa pasa de ~40 ms sobre un cuerpo de muchas caras (docs/auditorias/previa-comandos-*.md): se
# calculan en un proceso aparte para que la ventana no se congele. Sobre cuerpos chicos siguen en el proceso (< 33 ms).
TIPOS_PESADOS, CARAS_PESADAS = ("vaciado", "empalme", "chaflan", "primitiva", "patron"), 64


def _ids_cuerpo(p):
    """Ids de los cuerpos que nombra una operación: claves `cuerpo` (referencias a aristas y caras), `cuerpos` y `objetivo`."""
    ids, pila = set(), [p]
    while pila:
        x = pila.pop()
        if isinstance(x, dict):
            for k, v in x.items():
                if k in ("cuerpo", "cuerpos", "objetivo") and isinstance(v, str):
                    ids.add(v)
                elif k in ("cuerpos", "objetivo") and isinstance(v, list):
                    ids.update(e for e in v if isinstance(e, str))
                if isinstance(v, (dict, list)):
                    pila.append(v)
        elif isinstance(x, list):
            pila.extend(e for e in x if isinstance(e, (dict, list)))
    return ids


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


class Porcentaje(Entero):
    """Opacidad con casilla de activación y deslizador sincronizado con su número."""
    def __init__(self, clave, etiqueta, defecto=100, **kw):
        super().__init__(clave, etiqueta, defecto, 0, 100, **kw)


class Personalizado(Campo):
    """Campo con un widget propio: `crear(panel)` devuelve el widget y es quien avisa los cambios con
    `panel._cambiar(clave, valor)`. `ancho_completo` lo extiende sobre las dos columnas (sin etiqueta)."""

    def __init__(self, clave, etiqueta, crear, defecto=None, ancho_completo=False, **kw):
        super().__init__(clave, etiqueta, defecto, **kw)
        self.crear, self.ancho_completo = crear, ancho_completo


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
    # PL2 (Plasticity: teclas de opción a la vista): lo que hace cada tecla MIENTRAS el comando está
    # abierto, p. ej. {"Mayús": "simétrico", "Ctrl": "copiar"}; el panel lo muestra en el pie.
    MODIFICADORES = {}

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

    def preparar_panel(self, panel):
        """Conecta controles dependientes después de crear todos los campos."""

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


def hits_cuerpos(ids, estado):
    """Selecciones de cuerpo a partir de sus ids (un id suelto o una lista): lo mismo que elige el usuario."""
    if isinstance(ids, str):
        ids = [ids] if ids else []
    return hits([{"tipo": "cuerpo", "cuerpo": c} for c in ids], estado)


def acepta(filtros, hit):
    """¿La selección `hit` sirve para un campo con estos filtros? (misma regla que el visor)."""
    t, ref = hit.get("tipo"), hit.get("ref") or {}
    firma = ref.get("firma")
    geom = firma.get("geom") if isinstance(firma, dict) else None
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
        self._uso_inicio = self._uso_cambio = time.perf_counter() if registro_uso.activo is not None else None
        self._uso_cambios = 0
        self._uso_error = ""
        self.campos = comando.campos(ctx)
        self.valores = {c.clave: (list(c.defecto) if isinstance(c.defecto, list) else c.defecto) for c in self.campos}
        if ctx.op is not None:
            self.valores.update(comando.desde_op(ctx.op, ctx))
        self.valores.update(preajustes_ui.valores_iniciales(self))          # predeterminado del comando (preajustes)
        if valores:
            self.valores.update(valores)
        for c in self.campos:              # los huecos de la «o» de un texto (de antes o preelegidos) no van
            if isinstance(c, Seleccion) and "perfil" in c.filtros and self.valores.get(c.clave):
                try:
                    self.valores[c.clave] = [h for h in self.valores[c.clave]
                                             if not visor.es_hueco_texto(h, getattr(ctx, "estado", None))]
                except Exception:  # noqa: BLE001 — sin poder mirarlo, queda como estaba
                    pass
        self.widgets, self.etiquetas, self.filas_sel = {}, {}, {}
        self.activa = None
        self.ultima_op = None
        self._previa_ok = False
        self._previa_aislada = False    # la primera previa con éxito pasó el ensayo aislado (B-48): las siguientes van en vivo
        self._hijo_previa = self._op_hijo = self._pendiente_hijo = None
        self._previa_aparte = False     # la última previa pedida se calcula en el hijo: aceptar no espera su malla
        self._t_hijo = QTimer(self, interval=16)
        self._t_hijo.timeout.connect(self._recibir_previa)
        self._prisma_previa = None
        self.confirmar = None       # función(op) de la ventana: aplica y devuelve False si el editor debe seguir abierto

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
            if getattr(campo, "ancho_completo", False):
                et.hide()                                       # sin etiqueta: el widget ocupa las dos columnas
                self.grilla.addWidget(w, fila, 0, 1, 2)
            else:
                self.grilla.addWidget(et, fila, 0)
                self.grilla.addWidget(w, fila, 1)
            self.etiquetas[campo.clave], self.widgets[campo.clave] = et, w
        if preajustes_ui.tiene_preajustes(self):
            v.addWidget(preajustes_ui.FilaPreajustes(self))
        # B-105: en una ventana chica el cuerpo se desplaza con una barra y Aceptar/Cancelar quedan siempre visibles.
        self.desplazador = QScrollArea(widgetResizable=True, frameShape=QFrame.NoFrame)
        self.desplazador.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.desplazador.setWidget(cuerpo)
        v.addWidget(self.desplazador)

        # PL2 (Plasticity: teclas de opción a la vista): el pie del panel muestra qué hace cada
        # tecla MIENTRAS el comando está abierto; cada comando puede sumar las suyas en MODIFICADORES.
        teclas = [*(f"{k}: {d}" for k, d in getattr(comando, "MODIFICADORES", {}).items()),
                  "Enter: aceptar", "Esc: cancelar"]
        self.pie_teclas = QLabel("  ·  ".join(teclas), objectName="pie_comando", wordWrap=True)
        self.pie_teclas.setMaximumWidth(330)
        v.addWidget(self.pie_teclas)

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

        self._t_previa = QTimer(self, singleShot=True, interval=0)
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
        comando.preparar_panel(self)
        self._programar()
        self._registrar_uso("comando_abierto")

    # ------------------------------------------------------------ armado

    def _registrar_uso(self, tipo):
        if registro_uso.activo is None:
            return
        ahora = time.perf_counter()
        valores = {}
        for c in self.campos:
            valor = self.valores.get(c.clave)
            if isinstance(c, Expresion):
                try:
                    valor = self.ctx.evaluar(valor, c.tipo)
                except (ErrorExpresion, TypeError, ValueError):
                    pass
            valores[c.clave] = valor if isinstance(valor, (int, float, bool, str)) else len(valor) if isinstance(valor, list) else None
        registro_uso.activo.emitir(tipo, {"comando": self.comando.CLAVE, "valores": valores,
            "duracion_s": ahora - self._uso_inicio if self._uso_inicio is not None else 0,
            "cambios": self._uso_cambios, "editando": self.ctx.op is not None})

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
        if isinstance(campo, Porcentaje):
            w = QWidget()
            fila = QHBoxLayout(w)
            fila.setContentsMargins(0, 0, 0, 0)
            casilla = QCheckBox()
            casilla.setChecked(bool(self.valores.get("usar_opacidad", True)))
            numero = QSpinBox(minimum=0, maximum=100)
            deslizador = QSlider(Qt.Horizontal, minimum=0, maximum=100)
            numero.setValue(int(val))
            deslizador.setValue(int(val))
            casilla.toggled.connect(lambda b: self._cambiar("usar_opacidad", b))
            numero.valueChanged.connect(deslizador.setValue)
            deslizador.valueChanged.connect(numero.setValue)
            numero.valueChanged.connect(lambda n: self._cambiar(campo.clave, n))
            for hijo in (casilla, numero, deslizador):
                fila.addWidget(hijo)
            w.numero, w.deslizador, w.casilla = numero, deslizador, casilla
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
        if isinstance(campo, Personalizado):
            return campo.crear(self)
        if isinstance(campo, Info):
            w = QLabel(wordWrap=True)
            w.setMaximumWidth(220)
            w.setTextInteractionFlags(Qt.TextSelectableByMouse)
            return w
        raise TypeError(campo)

    # ------------------------------------------------------------ valores
    def ajustar_alto(self, disponible):
        """B-105: si el panel no entra en el visor, achica el cuerpo con barra; el pie nunca se tapa."""
        self.desplazador.setMaximumHeight(2 ** 24)          # el alto natural del cuerpo
        self.adjustSize()
        cuerpo = self.desplazador.height()
        otros = self.height() - cuerpo
        self.desplazador.setMaximumHeight(max(40, min(cuerpo, disponible - otros)))
        self.adjustSize()

    def _visible(self, campo):
        return campo.visible_si is None or bool(campo.visible_si(self.valores))

    def _actualizar_visibles(self):
        for c in self.campos:
            vis = self._visible(c)
            self.widgets[c.clave].setVisible(vis)
            if not getattr(c, "ancho_completo", False):
                self.etiquetas[c.clave].setVisible(vis)
        self._validar_expresiones()

    def _validar_expresiones(self):
        for c in self.campos:
            if isinstance(c, Expresion) and self._visible(c):
                w = self.widgets[c.clave]
                try:
                    val = self.ctx.evaluar(w.text(), c.tipo)
                    w.setToolTip(formato.tooltip_valor(val, c.tipo == ANGULO, c.tipo == ESCALAR))
                    w.setStyleSheet("")
                except ErrorExpresion as e:
                    w.setToolTip(str(e))
                    w.setStyleSheet(f"background: {temas.color('campo_error')};")

    def _cambiar(self, clave, valor):
        if registro_uso.activo is not None:
            self._uso_cambios += 1
            self._uso_cambio = time.perf_counter()
        self.valores[clave] = valor
        self._registrar_uso("comando_editado")
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
        elif isinstance(campo, Porcentaje):
            w.numero.setValue(int(valor))
        self.valores[clave] = valor if not isinstance(campo, Seleccion) else list(valor)
        self._actualizar_visibles()
        self._programar()

    # ------------------------------------------------------------ selección en la vista
    def _activar(self, campo):
        self.activa = campo
        for clave, fila in self.filas_sel.items():
            fila.set_estado(len(self.valores.get(clave) or []), campo is not None and clave == campo.clave)
        self.visor.set_filtro(campo.filtros if campo is not None else None)
        # en un campo de varios perfiles, tocar una letra elige el texto entero (como Fusion)
        self.visor.texto_entero = bool(campo is not None and campo.maximo is None and "perfil" in campo.filtros)

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
        grupo = None
        if "perfil" in campo.filtros:
            try:
                if self.visor.es_hueco_texto(hit):     # el hueco de la «o» de un texto es aire: no se elige
                    return
                if campo.maximo is None:
                    grupo = self.visor.hits_texto(hit)
            except Exception:  # noqa: BLE001 — sin el grupo, se elige la letra sola
                grupo = None
        if grupo:                           # una letra de un texto: entra (o sale) el texto entero
            refs = [h["ref"] for h in grupo]
            if repetida is not None:
                lista = [h for h in lista if h["ref"] not in refs]
            else:
                lista += [h for h in grupo if all(x["ref"] != h["ref"] for x in lista)]
        elif repetida is not None:          # clic sobre algo ya elegido: se quita (como Fusion)
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
        self._previa_aislada = False     # otra selección es otra geometría: la próxima previa vuelve a ensayarse aislada
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
            pass                             # arrastrando un asa: el cálculo ya pedido toma el último valor
        else:
            self._t_previa.start()
        if gestor is not None:
            gestor.actualizar()

    def valores_visibles(self):
        return {c.clave: self.valores.get(c.clave) for c in self.campos if self._visible(c)} | {
            k: v for k, v in self.valores.items() if k not in {c.clave for c in self.campos}}

    def _calcular_previa(self):
        inicio = time.perf_counter()
        try:
            self._calcular_previa_ahora()
        finally:
            ms = (time.perf_counter() - inicio) * 1000
            self._t_previa.setInterval(0 if ms < PREVIA_CUADRO_MS else min(int(ms), PREVIA_ESPERA_MAX_MS))

    def _calcular_previa_ahora(self):
        for c in self.campos:
            if isinstance(c, Info):
                try:
                    self.widgets[c.clave].setText(c.funcion(self.valores, self.ctx) or "")
                except Exception as e:  # noqa: BLE001 — un análisis que falla se informa en el panel
                    self.widgets[c.clave].setText(f"⚠ {e}")
        self._previa_ok = False
        self._previa_aparte = False
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
            self._cancelar_previa_hijo()
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
        if self._hijo_previa is not None:
            self._pendiente_hijo = op     # un solo cálculo activo; nunca se encolan los movimientos intermedios
            self._previa_aparte = True
            return
        if self._previa_pesada(op):
            self._previa_aparte = True
            self._iniciar_previa(op)
            return
        try:
            if self._previsualizar_prisma(op):
                return
            estado, avisos = self.ctx.doc.previsualizar(op, self.ctx.indice, en_vivo=self._previa_aislada)
            self._previa_aislada = True
        except Exception as e:  # noqa: BLE001 — se muestra el error del kernel como en Fusion
            self._mostrar(f"⚠ {e}")
            self._previa_vista(None)
            self.previa.emit(None)
            return
        self._previa_ok = True
        self._mostrar(" ".join(avisos), aviso=True)
        self._previa_vista(op)
        self.previa.emit(estado)

    def _previsualizar_prisma(self, op):
        p = op.p
        if (op.TIPO != "extrusion" or self.ctx.doc.motor != "opencascade"
                or p.get("operacion") != "nuevo" or p.get("tipo") != "solida"
                or p.get("inicio") != "plano" or p.get("extension") != "distancia"
                or p.get("extension2") != "distancia"
                or abs(self.ctx.evaluar(p["conicidad"], ANGULO)) > 1e-9
                or abs(self.ctx.evaluar(p["conicidad2"], ANGULO)) > 1e-9):
            self._prisma_previa = None
            return False
        from ..nucleo import geometria as geo, render_cpu as rc
        from ..nucleo.malla import Malla
        from ..timeline.operaciones import Contexto
        from .visor3d import aristas_cuerpo
        import numpy as np

        arrastrando = self.manipuladores is not None and self.manipuladores.arrastrando
        variables = {"distancia", "distancia2", "direccion", "medida", "simetrica", "invertir"}
        firma = (self.ctx.estado, repr({k: v for k, v in p.items() if k not in variables}),
                 self.visor.config.teselado, self.visor.config.angular)
        if self._prisma_previa is None or self._prisma_previa[0] != firma:
            plano, _ = op._caras(self.ctx.estado, Contexto(self.ctx.doc.parametros.valores()))
            unidad = type(op)(op.id, op.nombre, **dict(p, distancia="1 mm", direccion="un_lado", simetrica=False,
                                                      invertir=False))
            exacto, _ = self.ctx.doc.previsualizar(unidad, self.ctx.indice, en_vivo=self._previa_aislada)
            self._previa_aislada = True
            estado, prismas = exacto.copia(), {}
            for cid, c in estado.cuerpos.items():
                if cid in self.ctx.estado.cuerpos:
                    continue
                partes = rc._mallas_por_cara(c.forma, self.visor._deflexion(c.forma), self.visor.config.angular)
                v = np.concatenate([dato[1] for dato in partes])
                n = np.concatenate([dato[2] for dato in partes])
                seg = aristas_cuerpo(c.forma)
                try:
                    prismas[cid] = rc.PrismaVisual(v, n, seg, plano.origen, plano.normal)
                except geo.ErrorGeometria:   # no es un prisma recto desde su plano: lo muestra el camino exacto
                    self._prisma_previa = None
                    return False
                c.forma = Malla(v, np.arange(len(v)).reshape(-1, 3))
            self._prisma_previa = firma, estado, prismas
            if self.manipuladores is not None:
                self.manipuladores.actualizar()  # prepara también el apoyo del asa antes del primer movimiento
        if not arrastrando:
            return False    # el valor tecleado, y el asa al soltarse, siempre salen del kernel exacto
        d1 = self.ctx.evaluar(p["distancia"])
        modo = "simetrica" if p.get("simetrica") else p["direccion"]
        medida = "total" if p.get("simetrica") else p["medida"]
        d2 = self.ctx.evaluar(p["distancia2"]) if modo == "dos_lados" else None
        geo.exigir_distancias_extrusion(modo, d1, d2, medida)
        if modo == "simetrica":
            b = abs(d1) * (1 if medida == "mitad" else 0.5)
            a = -b
        elif modo == "dos_lados":
            a, b = min(0, d1, -d2), max(0, d1, -d2)
        else:
            a, b = 0, d1
        if p.get("invertir"):
            a, b = -a, -b
        _, estado, prismas = self._prisma_previa
        mallas = {cid: prisma.transformar(a, b) for cid, prisma in prismas.items()}
        estado._mallas_previa = mallas
        estado._cajas_previa = {cid: prisma.caja(a, b) for cid, prisma in prismas.items()}
        for cid, (v, _, _) in mallas.items():
            estado.cuerpos[cid].forma.vertices = v
        if self.visor._estado is not estado:
            self.previa.emit(estado)
        else:
            self.visor.actualizar_prismas(estado, mallas)
        self._previa_ok = True
        if self.mensaje.text():
            self._mostrar("")
        return True

    def _previa_pesada(self, op):
        if op.TIPO not in TIPOS_PESADOS or self.ctx.doc.motor != "opencascade":
            return False
        from ..nucleo import geometria as geo
        cuerpos = [self.ctx.estado.cuerpos.get(cid) for cid in _ids_cuerpo(op.p)]   # un id que ya no existe lo informa el camino normal
        return any(c is not None and len(geo.caras(c.forma)) >= CARAS_PESADAS for c in cuerpos)

    def _iniciar_previa(self, op):
        from ..nucleo.aislado import CalculoPendiente, TareaAislada
        try:
            self._hijo_previa = CalculoPendiente("previa_visual", {
                "receta": self.ctx.doc.a_dict(), "operacion": op.a_dict(), "indice": self.ctx.indice,
                "deflexion": self.visor.config.teselado or 0.05, "angular": self.visor.config.angular})
            self._op_hijo = op
            self._t_hijo.start()
            self._mostrar("Calculando vista previa en un proceso aparte…", aviso=True)
        except TareaAislada as e:
            self._mostrar(str(e), aviso=True)

    def _recibir_previa(self):
        from ..timeline.calculo_aislado import leer_previa_visual
        try:
            salida = self._hijo_previa.sondear()
            if salida is None:
                return
            estado, avisos = leer_previa_visual(salida, self.ctx.estado)
            self._previa_ok = self.ultima_op is not None and self.ultima_op.a_dict() == self._op_hijo.a_dict()
            self._mostrar(" ".join(avisos), aviso=True)
            if self._previa_ok:
                self._previa_vista(self._op_hijo)
            self.previa.emit(estado)
        except Exception as e:  # noqa: BLE001 — un hijo caído o vencido: la previa se apaga y el documento queda intacto
            self._previa_ok = False
            self._mostrar(f"⚠ {e}", aviso=True)
            self.previa.emit(None)
        self._t_hijo.stop()
        self._hijo_previa = None
        pendiente, self._pendiente_hijo = self._pendiente_hijo, None
        if pendiente is not None and pendiente.a_dict() != self._op_hijo.a_dict():
            self._iniciar_previa(pendiente)

    def _cancelar_previa_hijo(self):
        self._t_hijo.stop()
        if self._hijo_previa is not None:
            self._hijo_previa.cancelar()
            self._hijo_previa = None
        self._pendiente_hijo = None

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
        if registro_uso.activo is not None and texto and texto != self._uso_error:
            registrar_error(origen="comando", comando=self.comando.CLAVE, mensaje=texto)
            registro_uso.activo.emitir("comando_resultado", {"comando": self.comando.CLAVE, "exito": False})
        self._uso_error = texto
        self.mensaje.setObjectName("aviso_comando" if aviso else "mensaje_comando")
        self.mensaje.setStyleSheet(f"color: {temas.color('aviso' if aviso else 'error')};")
        self.mensaje.setText(texto)
        self.mensaje.setVisible(bool(texto))
        self.adjustSize()
        if hasattr(self.parent(), "reubicar"):
            self.parent().reubicar()        # el mensaje agranda el panel: que siga entrando en el visor

    # ------------------------------------------------------------ cierre
    def aceptar(self):
        if self._t_previa.isActive():
            self._t_previa.stop()
            self._calcular_previa()
        if self.comando.SIN_OP:
            try:
                self.comando.aplicar(self.valores, self.ctx)
            except (ErrorComando, ErrorExpresion, ErrorDocumento) as e:
                self._mostrar(str(e), aviso=True)
                return
            self._registrar_uso("comando_aceptado")
            self._cerrar()
            self.aceptado.emit(None)
            return
        if self.ultima_op is None:
            if not self.mensaje.text():
                self._mostrar("Faltan datos.", aviso=True)
            return
        if self.comando.PREVIA and not self._previa_ok and not self._previa_aparte:
            return                           # la operación falla: el mensaje rojo ya lo dice
        # Con la previa aparte en vuelo, caída o vencida, aceptar no espera: la operación se calcula exacta al aplicarla.
        op = self.ultima_op
        if self.confirmar is not None and not self.confirmar(op):
            return
        try:
            preajustes_ui.recordar_ultimo(self)
        except OSError:
            pass                              # no poder recordar los últimos valores no frena el comando
        self._registrar_uso("comando_aceptado")
        if registro_uso.activo is not None:
            registro_uso.activo.emitir("comando_resultado", {"comando": self.comando.CLAVE, "exito": True})
        self._cerrar()
        self.aceptado.emit(op)

    def cancelar(self):
        self._registrar_uso("comando_cancelado")
        self._cerrar()
        self.cancelado.emit()

    def _cerrar(self):
        self._t_previa.stop()
        self._cancelar_previa_hijo()
        self._prisma_previa = None
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
