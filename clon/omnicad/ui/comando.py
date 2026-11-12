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

from PySide6.QtCore import QPointF, QRectF, QSize, Qt, QTimer, Signal
from PySide6.QtGui import QColor, QPainter
from PySide6.QtWidgets import (QAbstractItemView, QApplication, QButtonGroup, QCheckBox, QComboBox, QFrame, QGridLayout,
                               QHBoxLayout, QHeaderView, QLabel, QLayout, QLineEdit, QMenu, QPlainTextEdit, QPushButton, QScrollArea,
                               QSizePolicy, QSlider, QSpinBox, QTabBar, QTableWidget, QTableWidgetItem, QToolButton, QVBoxLayout,
                               QWidget)

from ..timeline.documento import ErrorDocumento
from ..timeline.parametros import ANGULO, ESCALAR, LONGITUD, ErrorExpresion, con_unidad
from .. import registro_uso
from ..registro_uso.ganchos import aviso as registrar_aviso
from ..registro_uso.ganchos import error as registrar_error
from . import formato, preajustes_ui, temas
from .campo_expresion import CampoExpresion
from .formulario import (ANCHO_ETIQUETA, ANCHOS, NumeroDecimal, Seccion, armar_cabecera, describir_ref,
                         describir_seleccion, fila_mensaje, poner_mensaje, texto_filtros)
from .iconos import icono


# Vista previa «lo último gana» (P-41): cuánto se espera antes del próximo cálculo sigue a lo que costó el último.
PREVIA_CUADRO_MS, PREVIA_ESPERA_MAX_MS = 12, 220
# Operaciones cuya previa pasa de ~40 ms sobre un cuerpo de muchas caras (docs/auditorias/previa-comandos-*.md): se
# calculan en un proceso aparte para que la ventana no se congele. Sobre cuerpos chicos siguen en el proceso (< 33 ms).
TIPOS_PESADOS, CARAS_PESADAS = ("vaciado", "empalme", "chaflan", "primitiva", "patron", "multitransformar",
                                "desfase_cara", "engrosar", "sup_desfase"), 64
# Comandos cuya sección «Más opciones» quedó abierta (se recuerda mientras dure la sesión: no hace falta reabrirla cada vez).
_SECCIONES_ABIERTAS = set()


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
    """Un control del panel. Jerarquía (docs/auditorias/ui_paneles_2026-10-31.md): los campos son imprescindibles o
    frecuentes por defecto y van a la vista; `avanzado=True` los manda a la sección plegable «Más opciones» (solo lo poco
    frecuente: nunca lo necesario para completar la operación). `seccion` los pone en una sección plegable con ese título
    (la «Configuración de la forma» del Agujero): abierta por defecto, salvo que el título esté en `Comando.PLEGADAS`.
    `pestana` los lleva a otra pestaña del panel (la «Análisis» de Barrido). `grupo` los junta bajo un subtítulo;
    `visible_si` los muestra solo en el modo que corresponde; `etiqueta_si(valores)` cambia la etiqueta según el modo
    (p. ej. «Extensión total» o «Separación entre instancias»)."""

    def __init__(self, clave, etiqueta, defecto=None, visible_si=None, ayuda="", grupo=None, avanzado=False,
                 etiqueta_si=None, seccion=None, pestana=None):
        self.clave, self.etiqueta, self.defecto, self.visible_si, self.ayuda = clave, etiqueta, defecto, visible_si, ayuda
        self.grupo, self.avanzado, self.etiqueta_si, self.seccion, self.pestana = grupo, avanzado, etiqueta_si, seccion, pestana


class Seleccion(Campo):
    """Fila "Seleccionar": `filtros` es un subconjunto de visor3d.FILTROS; maximo=None = sin límite. `texto_boton` fija el
    texto del botón vacío (sin él, dice qué tipos acepta). `oculta`: se elige en el lienzo sin fila en el panel (Medir).
    `sin_resalte`: lo elegido no se pinta de azul (los análisis: el resalte taparía lo que pintan). `filtros_si(valores)`:
    lo que se puede elegir en la vista según el modo (Extruir sólida no toma curvas sueltas); sin él, `filtros`.
    `desvio(valores, hit, ctx)`: a qué campo pasa lo que se toca y no cumple la condición de este, como `(clave,
    otros_valores)`, o None si entra acá (Extruir: una cara de otro plano es el «Hasta objeto», B-338). Entra sola en
    ese campo, reemplazando lo que tenía; tocarla otra vez la saca."""

    def __init__(self, clave, etiqueta, filtros, minimo=1, maximo=1, texto_boton="", oculta=False, sin_resalte=False,
                 filtros_si=None, desvio=None, **kw):
        super().__init__(clave, etiqueta, [], **kw)
        self.filtros, self.minimo, self.maximo, self.texto_boton = set(filtros), minimo, maximo, texto_boton
        self.oculta, self.sin_resalte, self.filtros_si, self.desvio = oculta, sin_resalte, filtros_si, desvio


class ListaSeleccion(Seleccion):
    """Selección que se ve como tabla con + y ✕ (Perfiles y Raíles de Solevación). `celda(panel, i, n)`: el widget de la
    segunda columna de la fila i de n. La fila elegida queda en `valores["fila_<clave>"]`."""
    ancho_completo = True

    def __init__(self, clave, etiqueta, filtros, minimo=1, maximo=None, celda=None, **kw):
        super().__init__(clave, etiqueta, filtros, minimo, maximo, **kw)
        self.celda = celda


class Expresion(Campo):
    def __init__(self, clave, etiqueta, defecto="10 mm", tipo=LONGITUD, **kw):
        super().__init__(clave, etiqueta, defecto, **kw)
        self.tipo = tipo


class Opciones(Campo):
    """Lista desplegable. `opciones`: dict clave → texto (o (texto, ícono))."""

    def __init__(self, clave, etiqueta, opciones, defecto=None, **kw):
        super().__init__(clave, etiqueta, defecto if defecto is not None else next(iter(opciones)), **kw)
        self.opciones = opciones


class OpcionesVivas(Opciones):
    """Lista desplegable que depende de otros valores: `listar(valores)` da el dict de opciones y se vuelve a pedir con
    cada cambio (Designación según el Tamaño: un campo por tamaño serían miles)."""

    def __init__(self, clave, etiqueta, listar, defecto="", **kw):
        super().__init__(clave, etiqueta, {}, defecto, **kw)
        self.listar = listar


class Botones(Opciones):
    """Fila de íconos excluyentes (Tipo de agujero, Operación de Combinar…): el mismo valor que `Opciones`, un botón por
    opción y su nombre en el tooltip. `opciones`: dict clave → (texto, ícono)."""


class Casilla(Campo):
    def __init__(self, clave, etiqueta, defecto=False, **kw):
        super().__init__(clave, etiqueta, defecto, **kw)


class Alternar(Casilla):
    """Booleano que se ve como un botón con ícono que queda apretado («Cambiar dirección» de Nervio y Red). Con
    `icono_marcado`, apretado cambia de ícono y de nombre: es un modo que se cierra con Terminado («Definir punto de giro»)."""

    def __init__(self, clave, etiqueta, icono_boton, defecto=False, icono_marcado=None, **kw):
        super().__init__(clave, etiqueta, defecto, **kw)
        self.icono_boton, self.icono_marcado = icono_boton, icono_marcado


class Entero(Campo):
    def __init__(self, clave, etiqueta, defecto=1, minimo=1, maximo=10000, **kw):
        super().__init__(clave, etiqueta, defecto, **kw)
        self.minimo, self.maximo = minimo, maximo


class Deslizador(Entero):
    """Número y deslizador sincronizados (Repetición, Opacidad, Isocurvas del análisis); con `decimales`, no entero.
    `sufijo`: la unidad detrás del número («deg»)."""

    def __init__(self, clave, etiqueta, defecto=1, minimo=1, maximo=10000, decimales=0, sufijo="", **kw):
        super().__init__(clave, etiqueta, defecto, minimo, maximo, **kw)
        self.decimales, self.sufijo = decimales, sufijo


class DosTopes(Campo):
    """Dos números y un deslizador con dos topes (Ángulo de desmoldeo y Tolerancia): el valor es [mínimo, máximo] y un
    tope no cruza al otro."""

    def __init__(self, clave, etiqueta, defecto=(0.0, 1.0), minimo=0.0, maximo=1.0, decimales=1, sufijo="", **kw):
        super().__init__(clave, etiqueta, list(defecto), **kw)
        self.minimo, self.maximo, self.decimales, self.sufijo = minimo, maximo, decimales, sufijo


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
        self.ancho_completo = not etiqueta          # sin etiqueta el texto ocupa las dos columnas


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
        if tipo == ESCALAR and con_unidad(expr):         # lo teclea la persona: un factor o una relación no llevan unidad
            raise ErrorExpresion("Este valor no lleva unidad: escribí solo el número.")
        return self.parametros.evaluar(expr, tipo, estricto=tipo != ESCALAR)     # lo que se teclea, como en Fusion

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
    ANCHO_PANEL = None       # "simple" | "normal" | "ancho" (ui/formulario.ANCHOS); None = según la cantidad de campos
    PESTANA_PRINCIPAL = "Operación"     # título de la primera pestaña si el comando tiene campos con `pestana`
    INFO = None              # {"titulo", "texto", "consejos", "articulo"}: el botón «i» abre ese `ui/panel_info.PanelInfo`
    PLEGADAS = ()            # títulos de las secciones (`Campo.seccion`) que arrancan cerradas
    AYUDA = ""               # una o dos frases: se ven con el botón «?» de la cabecera (no ocupan el panel)
    # (clave del campo de modo, {valor: (título, ícono)}): la cabecera sigue al modo elegido (Patrón rectangular → circular)
    TITULOS_MODO = None

    def titulo_icono(self, valores):
        """(título, ícono) de la cabecera para estos valores: el del modo elegido si el comando tiene `TITULOS_MODO`."""
        if self.TITULOS_MODO:
            clave, tabla = self.TITULOS_MODO
            if valores.get(clave) in tabla:
                return tabla[valores[clave]]
        return self.TITULO, self.ICONO

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
        if ctx.op is not None:          # una versión de cálculo se conserva: editar no le cambia el cálculo a una receta vieja
            versiones = {k: v for k, v in ctx.op.p.items() if k.startswith("version_") and k in clase.PARAMS}
            return clase(ctx.op.id, ctx.op.nombre, ctx.op.suprimida, **{**versiones, **params})
        return clase(ctx.doc.nuevo_id(), self.nombre_nuevo(ctx), **params)

    def al_cerrar(self, ctx):
        """Limpieza al cerrar el panel (capas de análisis, colores…)."""

    def al_elegir(self, panel, clave):
        """Clic en la vista que completó un campo de selección (el centro de un cilindro empieza a dibujar el diámetro)."""

    def analizar_previa(self, v, ctx, estado, visor):
        """Vista previa lista: la pestaña Análisis la pinta (ver `comunes.con_analisis`)."""

    def previa_lista(self, panel, estado):
        """Vista previa lista, también en cada cuadro de un arrastre: el comando puede ajustar sus valores."""

    def al_tocar_paso(self, panel, op_id):
        """Clic en un paso del timeline con el panel abierto (Simetría y Patrón eligen operaciones así)."""
        panel.elegir_boceto(op_id)

    def preparar_panel(self, panel):
        """Conecta controles dependientes después de crear todos los campos."""

    def al_cambiar(self, panel, clave):
        """Gancho después de cambiar el valor de `clave` (a mano, con un asa o por código): permite ajustar otros
        campos o refrescar un widget propio. No debe cambiar `clave` otra vez sin cuidar la recursión."""

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
    hit.update(forma=e.forma, cuerpo=e.cuerpo, plano=e.plano, es_linea=e.tipo != "curva_boceto" or e.eje is not None)
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
    if t == "curva_boceto":        # B-131: donde va una línea no entra otra curva
        return "curva_boceto" in filtros or ("eje" in filtros and hit.get("es_linea", True))
    return t in filtros


def preseleccion(campos, seleccion):
    """Reparte lo que el usuario ya tenía elegido entre los campos de selección del comando, en orden
    (en Fusion, elegir primero y llamar al comando después llena sus selecciones)."""
    valores, restantes = {}, list(seleccion or [])
    defectos = {c.clave: c.defecto for c in campos}
    for c in campos:
        if not isinstance(c, Seleccion) or not restantes:
            continue
        filtros = set(c.filtros_si(defectos)) if c.filtros_si else c.filtros       # B-265: el modo de arranque manda
        compatibles = [h for h in restantes if acepta(filtros, h)]
        if c.maximo is not None:
            compatibles = compatibles[:c.maximo]
        if compatibles:
            valores[c.clave] = [dict(h, origen=h.get("origen", "previa")) for h in compatibles]
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
class _FilaBotones(QWidget):
    """La fila de `Botones`. Habla como el QComboBox que reemplaza (`findData`, `setCurrentIndex`, `currentData`,
    `currentIndexChanged`), así el panel, los preajustes y las pruebas la usan igual que a un desplegable."""
    currentIndexChanged = Signal(int)

    def __init__(self, opciones, parent=None):
        super().__init__(parent)
        self._claves, self._textos = list(opciones), [t[0] if isinstance(t, tuple) else t for t in opciones.values()]
        fila = QHBoxLayout(self)
        fila.setContentsMargins(0, 0, 0, 0)
        fila.setSpacing(2)
        self.grupo = QButtonGroup(self)
        for i, t in enumerate(opciones.values()):
            b = QToolButton(objectName="opcion_cmd", checkable=True, toolTip=self._textos[i], accessibleName=self._textos[i])
            b.setIcon(icono(t[1] if isinstance(t, tuple) else ""))
            b.setIconSize(QSize(20, 20))
            self.grupo.addButton(b, i)
            fila.addWidget(b)
        fila.addStretch(1)
        self.grupo.idToggled.connect(lambda i, marcado: marcado and self.currentIndexChanged.emit(i))

    def count(self):
        return len(self._claves)

    def findData(self, clave):
        return self._claves.index(clave) if clave in self._claves else -1

    def findText(self, texto):
        return self._textos.index(texto) if texto in self._textos else -1

    def itemData(self, i):
        return self._claves[i]

    def itemText(self, i):
        return self._textos[i]

    def currentIndex(self):
        return self.grupo.checkedId()

    def currentData(self):
        return self._claves[self.grupo.checkedId()] if self.grupo.checkedId() >= 0 else None

    def currentText(self):
        return self._textos[self.grupo.checkedId()] if self.grupo.checkedId() >= 0 else ""

    def setCurrentIndex(self, i):
        self.grupo.button(i).setChecked(True)

    def boton(self, clave):
        return self.grupo.button(self.findData(clave))


class _DeslizadorDoble(QWidget):
    """Barra con dos topes arrastrables, en un rango [minimo, maximo]. `movido(i, valor)` al arrastrar el tope i."""
    movido = Signal(int, float)
    MARGEN = 6

    def __init__(self, minimo, maximo, parent=None):
        super().__init__(parent)
        self.minimo, self.maximo, self.valores, self._activo = float(minimo), float(maximo), [float(minimo), float(maximo)], None
        self.setFixedHeight(20)
        self.setMinimumWidth(80)

    def x_de(self, i):
        util = max(self.width() - 2 * self.MARGEN, 1)
        return self.MARGEN + util * (self.valores[i] - self.minimo) / (self.maximo - self.minimo)

    def _valor_en(self, x):
        util = max(self.width() - 2 * self.MARGEN, 1)
        return self.minimo + min(max((x - self.MARGEN) / util, 0.0), 1.0) * (self.maximo - self.minimo)

    def poner(self, a, b):
        self.valores = [float(a), float(b)]
        self.update()

    def mousePressEvent(self, e):
        x = e.position().x()
        self._activo = min((0, 1), key=lambda i: abs(self.x_de(i) - x))
        self.mouseMoveEvent(e)

    def mouseMoveEvent(self, e):
        if self._activo is None:
            return
        i, v = self._activo, self._valor_en(e.position().x())
        v = min(v, self.valores[1]) if i == 0 else max(v, self.valores[0])
        self.movido.emit(i, v)

    def mouseReleaseEvent(self, _e):
        self._activo = None

    def paintEvent(self, _e):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        y = self.height() / 2
        tema = self.palette()
        p.setPen(tema.mid().color())
        p.drawLine(QPointF(self.MARGEN, y), QPointF(self.width() - self.MARGEN, y))
        x0, x1 = self.x_de(0), self.x_de(1)
        p.setPen(QColor(tema.text().color()))
        p.drawLine(QPointF(x0, y), QPointF(x1, y))
        p.setBrush(tema.text())
        for x in (x0, x1):
            p.drawRoundedRect(QRectF(x - 2, y - 7, 4, 14), 1, 1)


class _FilaDosTopes(QWidget):
    """Los dos números arriba y el deslizador doble abajo. `cambiado(mínimo, máximo)` con cada cambio."""
    cambiado = Signal(float, float)

    def __init__(self, campo, valor, parent=None):
        super().__init__(parent)
        v = QVBoxLayout(self)
        v.setContentsMargins(0, 0, 0, 0)
        v.setSpacing(2)
        fila = QHBoxLayout()
        fila.setContentsMargins(0, 0, 0, 0)
        self.numero_a, self.numero_b = (NumeroDecimal(decimals=campo.decimales, minimum=campo.minimo, maximum=campo.maximo,
                                                       suffix=f" {campo.sufijo}" if campo.sufijo else "") for _ in range(2))
        fila.addWidget(self.numero_a)
        fila.addStretch(1)
        fila.addWidget(self.numero_b)
        v.addLayout(fila)
        self.doble = _DeslizadorDoble(campo.minimo, campo.maximo)
        v.addWidget(self.doble)
        self.poner(valor)
        self.numero_a.valueChanged.connect(lambda n: self._cambiar(0, n))
        self.numero_b.valueChanged.connect(lambda n: self._cambiar(1, n))
        self.doble.movido.connect(self._cambiar)

    def poner(self, valor):
        """Sin avisar: lo pide `PanelComando.set_valores`."""
        for w, x in ((self.numero_a, valor[0]), (self.numero_b, valor[1])):
            w.blockSignals(True)
            w.setValue(x)
            w.blockSignals(False)
        self.doble.poner(*valor)

    def _cambiar(self, i, n):
        a, b = self.numero_a.value(), self.numero_b.value()
        a, b = (min(n, b), b) if i == 0 else (a, max(n, a))
        self.poner((a, b))
        self.cambiado.emit(a, b)


class _BotonElidido(QPushButton):
    """Botón cuyo texto se corta con «…» al ancho disponible: un nombre largo nunca ensancha el panel."""

    def __init__(self, *a, **k):
        super().__init__(*a, **k)
        self._completo, self._elidir = "", False

    def poner(self, texto, elidir):
        self._completo, self._elidir = texto, elidir
        self._pintar()

    def _pintar(self):
        if self._elidir and self.width() > 60:
            # B-282: se corta el final (el cuerpo), nunca el rasgo que distingue lo elegido; el nombre entero, en el tooltip
            self.setText(self.fontMetrics().elidedText(self._completo, Qt.ElideRight, self.width() - 34))
        else:
            self.setText(self._completo)

    def resizeEvent(self, e):
        super().resizeEvent(e)
        if self._elidir:
            self._pintar()


class _FilaLista(QWidget):
    """`ListaSeleccion`: etiqueta arriba, una fila por elemento y debajo + (elegir más), ✕ (quitar la fila) y ▲▼ (reordenar)."""
    activar = Signal(object)
    limpiar = Signal(object)
    quitar = Signal(object, int)
    mover = Signal(object, int, int)

    def __init__(self, campo, panel):
        super().__init__()
        self.campo, self.panel, self._items = campo, panel, None
        caja = QVBoxLayout(self)
        caja.setContentsMargins(0, 0, 0, 0)
        caja.setSpacing(2)
        caja.addWidget(QLabel(campo.etiqueta))
        self.tabla = QTableWidget(0, 2 if campo.celda else 1, objectName="lista_seleccion", showGrid=False,
                                  selectionBehavior=QAbstractItemView.SelectRows, selectionMode=QAbstractItemView.SingleSelection,
                                  editTriggers=QAbstractItemView.NoEditTriggers)
        self.tabla.horizontalHeader().hide()
        self.tabla.verticalHeader().hide()
        self.tabla.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        self.tabla.setMaximumHeight(92)
        self.tabla.itemSelectionChanged.connect(self._fila_elegida)
        caja.addWidget(self.tabla)
        pie = QHBoxLayout()
        pie.setSpacing(2)
        self.mas = QToolButton(text="+", checkable=True, toolTip="Agregar")
        self.mas.clicked.connect(lambda: self.activar.emit(self))
        self.menos = QToolButton(text="✕", toolTip="Quitar la fila elegida")
        self.menos.clicked.connect(lambda: self._con_fila(lambda i: self.quitar.emit(self, i)))
        self.arriba = QToolButton(text="▲", toolTip="Subir la fila elegida")
        self.arriba.clicked.connect(lambda: self._con_fila(lambda i: self.mover.emit(self, i, i - 1)))
        self.abajo = QToolButton(text="▼", toolTip="Bajar la fila elegida")
        self.abajo.clicked.connect(lambda: self._con_fila(lambda i: self.mover.emit(self, i, i + 1)))
        for b in (self.mas, self.menos, self.arriba, self.abajo):
            pie.addWidget(b)
        pie.addStretch(1)
        caja.addLayout(pie)

    def _con_fila(self, accion):
        if self.tabla.currentRow() >= 0:
            accion(self.tabla.currentRow())

    def _fila_elegida(self):
        self.panel._cambiar(f"fila_{self.campo.clave}", self.tabla.currentRow())

    def set_estado(self, n, activa, _descripcion="", _detalle="", vacio="", items=()):
        self.mas.setChecked(activa)
        self.tabla.setToolTip(vacio)
        items = list(items) or [f"Elemento {i + 1}" for i in range(n)]
        if items == self._items:
            return
        self._items = items
        self.tabla.blockSignals(True)
        self.tabla.setRowCount(n)
        for i, texto in enumerate(items):
            self.tabla.setItem(i, 0, QTableWidgetItem(texto))
            if self.campo.celda:
                self.tabla.setCellWidget(i, 1, self.campo.celda(self.panel, i, n))
        self.tabla.blockSignals(False)


class _FilaSeleccion(QWidget):
    """Fila «Seleccionar». Sin descripción (paneles de boceto) dice «N seleccionados»; con ella (paneles de comando)
    muestra qué es lo elegido («Cara +Z · Caja1», «3 aristas · Caja1»), con el detalle en el tooltip y, si hay
    varios, un menú ▾ para revisarlos y quitar uno a uno. ✕ limpia todo."""
    activar = Signal(object)
    limpiar = Signal(object)
    quitar = Signal(object, int)         # (fila, posición del elemento que se quita)

    def __init__(self, campo, parent=None):
        super().__init__(parent)
        self.campo = campo
        self._items = []
        h = QHBoxLayout(self)
        h.setContentsMargins(0, 0, 0, 0)
        h.setSpacing(2)
        self.boton = _BotonElidido(objectName="seleccion_cmd")
        self.boton.setIcon(icono("seleccionar"))
        self.boton.setIconSize(QSize(14, 14))
        self.boton.setCursor(Qt.PointingHandCursor)
        self.boton.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Fixed)        # el texto no ensancha el panel
        self.boton.clicked.connect(lambda: self.activar.emit(self))
        self.revisar = QToolButton(text="▾", popupMode=QToolButton.InstantPopup)
        self.revisar.setToolTip("Revisar lo elegido y quitar elementos uno a uno")
        self.menu = QMenu(self.revisar)
        self.revisar.setMenu(self.menu)
        self.menu.aboutToShow.connect(self._armar_menu)
        self.borrar = QToolButton(text="✕")
        self.borrar.setToolTip("Borrar la selección")
        self.borrar.clicked.connect(lambda: self.limpiar.emit(self))
        h.addWidget(self.boton, 1)
        h.addWidget(self.revisar)
        h.addWidget(self.borrar)
        self.set_estado(0, False)

    def _armar_menu(self):
        self.menu.clear()
        for i, texto in enumerate(self._items):
            self.menu.addAction(f"Quitar: {texto}").triggered.connect(lambda _=False, i=i: self.quitar.emit(self, i))

    def set_estado(self, n, activa, descripcion="", detalle="", vacio="", items=()):
        """`descripcion`/`detalle`/`vacio`/`items` los pasa el panel de comando; sin ellos queda el texto simple."""
        propio = bool(descripcion) or (n == 0 and bool(vacio))
        if n == 0 and getattr(self.campo, "texto_boton", ""):
            texto_vacio = self.campo.texto_boton
        elif n == 0 and len(vacio) > 26:                  # una lista larga de tipos no entra en el botón: queda en el tooltip
            texto_vacio = "Elegir en la vista"
        else:
            texto_vacio = vacio
        texto = descripcion or (texto_vacio if n == 0 and vacio else (
            "Seleccionar" if n == 0 else (f"{n} seleccionado" if n == 1 else f"{n} seleccionados")))
        self._items = list(items)
        self.boton.setToolTip(detalle or vacio)
        self.boton.poner(texto, propio)
        self.boton.setProperty("activa", activa)
        self.boton.setProperty("lleno", n > 0)
        self.boton.style().unpolish(self.boton)
        self.boton.style().polish(self.boton)
        self.borrar.setVisible(n > 0)
        self.revisar.setVisible(n > 1 and bool(descripcion))


def tramo_previa(modo, d1, d2, medida, invertir):
    """(a, b): de dónde a dónde, sobre la normal del perfil, va el prisma de la previa rápida de Extruir. La misma regla
    que el núcleo (`extruir_avanzado`, `_extrusion_basica`): en «Dos lados» cada distancia es una magnitud (B-205)."""
    if modo == "simetrica":
        b = abs(d1) * (1 if medida == "mitad" else 0.5)
        a = -b
    elif modo == "dos_lados":
        a, b = -abs(d2), abs(d1)
    else:
        a, b = 0, d1
    return (-a, -b) if invertir else (a, b)


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
        self._previa_cortada = False
        self.cerrando = False           # True desde `_cerrar`: la ventana no redibuja el estado viejo antes de cerrar
        self._previa_aparte = False     # la última previa pedida se calcula en el hijo: aceptar no espera su malla
        self._t_hijo = QTimer(self, interval=16)
        self._t_hijo.timeout.connect(self._recibir_previa)
        self._prisma_previa = None
        self.confirmar = None       # función(op) de la ventana: aplica y devuelve False si el editor debe seguir abierto

        v = QVBoxLayout(self)
        v.setContentsMargins(0, 0, 0, 0)
        v.setSpacing(0)
        v.setSizeConstraint(QLayout.SetFixedSize)
        self.ancho_panel = ANCHOS[comando.ANCHO_PANEL or ("simple" if len(self.campos) <= 6 else "normal")]
        self._por_clave = {c.clave: c for c in self.campos}
        self.boton_preajustes = None
        if preajustes_ui.tiene_preajustes(self):      # UI-4: los preajustes van en la cabecera, no en una fila aparte
            self.boton_preajustes = preajustes_ui.BotonPreajustes(self)
        self.boton_ayuda = QToolButton(text="?", checkable=True, toolTip="Qué hace este comando")
        self.boton_ayuda.setFocusPolicy(Qt.NoFocus)  # Tab empieza en los campos, no en la cabecera (Esc ya cancela)
        cab, self.icono_titulo, self.titulo = armar_cabecera(
            self, self.cancelar, [w for w in (self.boton_preajustes, self.boton_ayuda) if w is not None])
        self.boton_ayuda.setVisible(bool(comando.AYUDA))      # con padre: suelto se mostraría como ventana (B-136)
        v.addWidget(cab)
        self._titulo_actual = None
        self._actualizar_titulo()
        self.ayuda = QLabel(comando.AYUDA, objectName="pie_comando", wordWrap=True)
        self.ayuda.setMaximumWidth(self.ancho_panel)
        self.ayuda.hide()
        self.boton_ayuda.toggled.connect(lambda b: (self.ayuda.setVisible(b), self._reubicar()))   # ver la ayuda no recalcula nada
        v.addWidget(self.ayuda)

        cuerpo = QWidget()
        marco = QVBoxLayout(cuerpo)
        marco.setContentsMargins(10, 8, 10, 6)
        marco.setSpacing(4)
        self.grilla = self._grilla_nueva()
        marco.addLayout(self.grilla)
        avanzados = [c for c in self.campos if c.avanzado and not c.pestana]
        self.seccion = None
        if avanzados:
            self.seccion = Seccion("Más opciones", abierta=comando.CLAVE in _SECCIONES_ABIERTAS or bool(self._resumen_avanzados()))
            self.seccion.plegada.connect(self._seccion_alternada)
            marco.addWidget(self.seccion)
        self.plegables = {}                # título de `Campo.seccion` → Seccion
        self.paginas = {}                  # título de `Campo.pestana` → su página
        marcos = {None: marco}             # pestaña → marco donde se apilan sus grillas y secciones
        libres = {None: self.grilla}       # pestaña → grilla vigente de los campos sueltos
        en_seccion = {None: False}         # pestaña → ¿el campo anterior estaba en una sección plegable?
        self.rotulos = []                  # (rótulo del grupo, [claves]) → se ve si algún campo del grupo se ve
        ultimo = {}                        # por grilla (principal / «Más opciones»): (grupo, claves del rótulo vigente)
        for campo in self.campos:
            p = campo.pestana
            if p is not None and p not in self.paginas:
                self.paginas[p] = QWidget()
                marcos[p] = QVBoxLayout(self.paginas[p])
                marcos[p].setContentsMargins(10, 8, 10, 6)
                marcos[p].setSpacing(4)
                libres[p] = self._grilla_nueva()
                marcos[p].addLayout(libres[p])
                en_seccion[p] = False
            if campo.avanzado and p is None:
                grilla = self.seccion.grilla
            elif campo.seccion:
                grilla = self._plegable(campo.seccion, marcos[p]).grilla
                en_seccion[p] = True
            else:
                if en_seccion[p]:              # un campo suelto después de una sección va debajo de ella
                    libres[p] = self._grilla_nueva()
                    marcos[p].insertLayout(self._antes_de_mas_opciones(marcos[p]), libres[p])
                    en_seccion[p] = False
                grilla = libres[p]
            fila = grilla.rowCount()
            if campo.grupo and (ultimo.get(id(grilla)) or (None,))[0] != campo.grupo:
                rotulo = QLabel(campo.grupo, objectName="grupo_cmd")
                grilla.addWidget(rotulo, fila, 0, 1, 2)
                claves = [campo.clave]
                self.rotulos.append((rotulo, claves))
                ultimo[id(grilla)] = (campo.grupo, claves)
                fila += 1
            elif campo.grupo:
                ultimo[id(grilla)][1].append(campo.clave)
            else:
                ultimo[id(grilla)] = None
            et = QLabel(campo.etiqueta_si(self.valores) if campo.etiqueta_si else campo.etiqueta,
                        objectName="etiqueta_cmd", wordWrap=True)
            et.setFixedWidth(ANCHO_ETIQUETA)
            if campo.ayuda:
                et.setToolTip(campo.ayuda)
            w = self._widget(campo)
            if getattr(campo, "ancho_completo", False):
                et.hide()                                       # sin etiqueta: el widget ocupa las dos columnas
                grilla.addWidget(w, fila, 0, 1, 2)
            else:
                grilla.addWidget(et, fila, 0, Qt.AlignTop if isinstance(campo, Info) else Qt.AlignVCenter)
                grilla.addWidget(w, fila, 1)
            self.etiquetas[campo.clave], self.widgets[campo.clave] = et, w
        # B-105: en una ventana chica el cuerpo se desplaza con una barra y Aceptar/Cancelar quedan siempre visibles.
        self.desplazador = QScrollArea(widgetResizable=True, frameShape=QFrame.NoFrame)
        self.desplazador.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)     # solo si un widget propio no entra: no se recorta en silencio
        self.desplazador.setFixedWidth(self.ancho_panel)
        self.barra_pestanas = None
        if self.paginas:
            self.pagina_principal = cuerpo
            cuerpo = self._armar_pestanas(cuerpo, v)
        self.desplazador.setWidget(cuerpo)
        v.addWidget(self.desplazador)

        # PL2 (Plasticity: teclas de opción a la vista): el pie muestra las teclas de opción del comando (solo si tiene);
        # Enter y Esc ya están en los tooltips de Aceptar y Cancelar.
        teclas = [*(f"{k}: {d}" for k, d in getattr(comando, "MODIFICADORES", {}).items()),
                  "Enter: aceptar", "Esc: cancelar"]
        self.pie_teclas = QLabel("  ·  ".join(teclas), objectName="pie_comando", wordWrap=True)
        self.pie_teclas.setMaximumWidth(self.ancho_panel)
        self.pie_teclas.setVisible(bool(getattr(comando, "MODIFICADORES", {})))
        v.addWidget(self.pie_teclas)

        # Estado: una línea reservada (no salta el panel al aparecer o desaparecer un mensaje); el símbolo y el color dicen
        # de qué clase es: instrucción pendiente, valor inválido, advertencia, cálculo en curso o error.
        zona, self.icono_mensaje, self.mensaje = fila_mensaje(self.ancho_panel, self.fontMetrics().height() + 8)
        v.addWidget(zona)
        pie = QHBoxLayout()
        pie.setContentsMargins(10, 4, 10, 8)
        self.boton_info = None
        if comando.INFO:
            self.boton_info = QToolButton(text="i", toolTip="Información de este comando")
            self.boton_info.setFixedSize(16, 16)
            self.boton_info.setStyleSheet("QToolButton { background: #7d8791; color: white; border-radius: 8px; font-weight: bold; }")
            self.boton_info.clicked.connect(self._abrir_info)
            pie.addWidget(self.boton_info)
        pie.addStretch(1)
        self.boton_ok = QPushButton(comando.TEXTO_ACEPTAR, objectName="boton_primario", toolTip="Aceptar (Enter)")
        self.boton_ok.clicked.connect(self.aceptar)
        self.boton_cancelar = QPushButton("Cancelar", toolTip="Cancelar (Esc)")
        self.boton_cancelar.clicked.connect(self.cancelar)
        pie.addWidget(self.boton_ok)
        pie.addWidget(self.boton_cancelar)
        v.addLayout(pie)
        if self.boton_preajustes is not None:       # Tab empieza en los campos: «⋯» queda después de Cancelar
            QWidget.setTabOrder(self.boton_cancelar, self.boton_preajustes)

        self._t_previa = QTimer(self, singleShot=True, interval=0)
        self._t_reubicar = QTimer(self, singleShot=True, interval=0, timeout=self._reubicar_ahora)   # B-113: un mensaje de varias líneas asienta su alto recién al volver al bucle de eventos
        self._t_previa.timeout.connect(self._calcular_previa)
        self.manipuladores = None            # GestorManipuladores si el comando tiene asas en la vista
        if (type(comando).manipuladores is not Comando.manipuladores
                or type(comando).previa_vista is not Comando.previa_vista):
            from .manipuladores import GestorManipuladores
            self.manipuladores = GestorManipuladores(self)
        self.visor.entidad_elegida.connect(self._elegida)
        self._actualizar_visibles()
        self._refrescar_seleccion()
        primera = next((c for c in self.campos if isinstance(c, Seleccion) and self._a_la_vista(c)
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
        valores, libres = {}, []
        for c in self.campos:
            valor = self.valores.get(c.clave)
            if isinstance(c, Expresion):
                try:
                    valor = self.ctx.evaluar(valor, c.tipo)
                except (ErrorExpresion, TypeError, ValueError):
                    pass
            valores[c.clave] = (valor if isinstance(valor, (int, float, bool, str)) else len(valor) if isinstance(valor, list)
                                else valor.get("nombre") if isinstance(valor, dict) else None)   # un aspecto: su nombre
            if isinstance(c, Texto):
                libres.append(c.clave)                        # texto libre: se guarda como largo salvo en detallado
        registro_uso.activo.emitir(tipo, {"comando": self.comando.CLAVE, "valores": valores,
            "duracion_s": ahora - self._uso_inicio if self._uso_inicio is not None else 0,
            "cambios": self._uso_cambios, "editando": self.ctx.op is not None}, libres=libres)

    def _antes_de_mas_opciones(self, marco):
        """Posición de `marco` para agregar algo: «Más opciones» siempre queda al final."""
        i = marco.indexOf(self.seccion) if self.seccion is not None else -1
        return i if i >= 0 else marco.count()

    def _plegable(self, titulo, marco):
        """La sección plegable `titulo`, creada la primera vez que aparece."""
        s = self.plegables.get(titulo)
        if s is None:
            s = self.plegables[titulo] = Seccion(titulo, abierta=titulo not in self.comando.PLEGADAS)
            s.plegada.connect(lambda _a: self._reubicar())        # plegar no recalcula: solo cambia lo que se ve
            marco.insertWidget(self._antes_de_mas_opciones(marco), s)
        return s

    def _armar_pestanas(self, principal, v):
        """Barra Operación / Análisis arriba del cuerpo. Devuelve el widget con todas las páginas: se ve solo la de la
        pestaña elegida y el panel se ajusta a ella (un QStackedWidget mediría siempre lo que la más alta)."""
        self.barra_pestanas = QTabBar(objectName="pestanas_cmd", drawBase=False, expanding=False)
        self.barra_pestanas.addTab(self.comando.PESTANA_PRINCIPAL)
        for titulo in self.paginas:
            self.barra_pestanas.addTab(titulo)
        v.addWidget(self.barra_pestanas)
        todas = QWidget()
        lista = QVBoxLayout(todas)
        lista.setContentsMargins(0, 0, 0, 0)
        lista.setSpacing(0)
        for pagina in (principal, *self.paginas.values()):
            lista.addWidget(pagina)
            pagina.setVisible(pagina is principal)
        lista.addStretch(1)
        self.barra_pestanas.currentChanged.connect(self._cambiar_pestana)
        return todas

    def _pestana_actual(self):
        """Título de la pestaña a la vista; None = la principal (Operación)."""
        i = self.barra_pestanas.currentIndex() if self.barra_pestanas is not None else 0
        return None if i <= 0 else self.barra_pestanas.tabText(i)

    def _cambiar_pestana(self, _i):
        actual = self._pestana_actual()
        self.pagina_principal.setVisible(actual is None)
        for titulo, pagina in self.paginas.items():
            pagina.setVisible(titulo == actual)
        self._activar(next((c for c in self.campos if isinstance(c, Seleccion) and self._a_la_vista(c)
                            and not self.valores.get(c.clave)), None))
        self._reubicar()                     # cambiar de pestaña no recalcula: solo cambia lo que se ve

    def _widget(self, campo):
        val = self.valores.get(campo.clave)
        if isinstance(campo, Seleccion):
            w = _FilaLista(campo, self) if isinstance(campo, ListaSeleccion) else _FilaSeleccion(campo)
            if isinstance(campo, ListaSeleccion):
                w.mover.connect(lambda f, a, b: self._reordenar(f.campo, a, b))
            w.activar.connect(lambda f: self._activar(f.campo))
            w.limpiar.connect(lambda f: self._limpiar(f.campo))
            w.quitar.connect(lambda f, i: self._quitar(f.campo, i))
            self.filas_sel[campo.clave] = w
            return w
        if isinstance(campo, Expresion):
            w = CampoExpresion(str(val), self.ctx, campo.tipo)
            w.textChanged.connect(lambda t, c=campo: self._cambiar(c.clave, t.strip()))
            return w
        if isinstance(campo, Botones):
            w = _FilaBotones(campo.opciones)
            w.setCurrentIndex(max(w.findData(val), 0))
            w.currentIndexChanged.connect(lambda _i, c=campo, w=w: self._cambiar(c.clave, w.currentData()))
            return w
        if isinstance(campo, Opciones):
            w = QComboBox()
            w.setSizeAdjustPolicy(QComboBox.AdjustToMinimumContentsLengthWithIcon)      # una opción larga no ensancha el panel
            w.setMinimumContentsLength(8)
            if isinstance(campo, OpcionesVivas):
                campo.opciones = campo.listar(self.valores)
            for k, texto in campo.opciones.items():
                if isinstance(texto, tuple):
                    w.addItem(icono(texto[1]), texto[0], k)
                else:
                    w.addItem(texto, k)
            i = w.findData(val)
            w.setCurrentIndex(max(i, 0))
            w.currentIndexChanged.connect(lambda _i, c=campo, w=w: self._cambiar(c.clave, w.currentData()))
            return w
        if isinstance(campo, Alternar):
            w = QToolButton(objectName="opcion_cmd", checkable=True, checked=bool(val), toolTip=campo.etiqueta,
                            accessibleName=campo.etiqueta)
            w.setIcon(icono(campo.icono_boton))
            w.setIconSize(QSize(20, 20))
            w.toggled.connect(lambda b, c=campo: self._cambiar(c.clave, b))
            if campo.icono_marcado:
                def modo(b, w=w, c=campo):
                    w.setIcon(icono(c.icono_marcado if b else c.icono_boton))
                    w.setToolTip("Terminado" if b else c.etiqueta)
                w.toggled.connect(modo)
                modo(bool(val))
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
        if isinstance(campo, Deslizador):
            w = QWidget()
            fila = QHBoxLayout(w)
            fila.setContentsMargins(0, 0, 0, 0)
            escala = 10 ** campo.decimales
            numero = (NumeroDecimal(decimals=campo.decimales, minimum=campo.minimo, maximum=campo.maximo,
                                     suffix=f" {campo.sufijo}" if campo.sufijo else "") if campo.decimales
                      else QSpinBox(minimum=campo.minimo, maximum=campo.maximo))
            deslizador = QSlider(Qt.Horizontal, minimum=int(campo.minimo * escala), maximum=int(campo.maximo * escala))
            numero.setValue(val)
            deslizador.setValue(round(val * escala))
            numero.valueChanged.connect(lambda n, d=deslizador: d.setValue(round(n * escala)))
            deslizador.valueChanged.connect(lambda x, n=numero: n.setValue(x / escala if campo.decimales else x))
            numero.valueChanged.connect(lambda n, c=campo: self._cambiar(c.clave, n))
            deslizador.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Fixed)   # no ensancha el panel: toma lo que sobra
            fila.addWidget(numero)
            fila.addWidget(deslizador, 1)
            w.numero, w.deslizador = numero, deslizador
            return w
        if isinstance(campo, DosTopes):
            w = _FilaDosTopes(campo, val)
            w.cambiado.connect(lambda a, b, c=campo: self._cambiar(c.clave, [a, b]))
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
            w.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Preferred)
            w.setTextInteractionFlags(Qt.TextSelectableByMouse)
            return w
        raise TypeError(campo)

    # ------------------------------------------------------------ cabecera, secciones y estado
    @staticmethod
    def _grilla_nueva():
        g = QGridLayout()
        g.setContentsMargins(0, 0, 0, 0)
        g.setHorizontalSpacing(10)
        g.setVerticalSpacing(5)
        g.setColumnMinimumWidth(0, ANCHO_ETIQUETA)
        g.setColumnStretch(1, 1)
        return g

    def _actualizar_titulo(self):
        """La cabecera sigue a la operación activa: cambia con el modo (Patrón rectangular → circular) y dice si se edita."""
        titulo, ico = self.comando.titulo_icono(self.valores)
        if (titulo, ico) == self._titulo_actual:
            return
        self._titulo_actual = (titulo, ico)
        completo = titulo.upper() if self.ctx.op is None else f"EDITAR {titulo.upper()}"
        # Un título largo se corta con «…» (con el completo en el tooltip): nunca ensancha el panel.
        sitio = self.ancho_panel - (122 if self.boton_preajustes is not None else 96)       # lo que dejan el ícono y los botones
        self.titulo.setText(self.titulo.fontMetrics().elidedText(completo, Qt.ElideRight, sitio)
                            if self.titulo.fontMetrics().horizontalAdvance(completo) * 1.15 > sitio else completo)
        self.titulo.setToolTip(completo)
        self.icono_titulo.setPixmap(icono(ico).pixmap(18, 18))

    def _reubicar(self):
        """El panel cambió de alto (mensaje, ayuda, sección): que siga entrando en el visor."""
        self._reubicar_ahora()
        self._t_reubicar.start()          # y otra vez cuando el layout ya asentó las alturas que dependen del ancho

    def _reubicar_ahora(self):
        self.adjustSize()
        if hasattr(self.parent(), "reubicar"):
            self.parent().reubicar()

    def _seccion_alternada(self, abierta):
        (_SECCIONES_ABIERTAS.add if abierta else _SECCIONES_ABIERTAS.discard)(self.comando.CLAVE)
        self._reubicar()                     # plegar no recalcula la vista previa: solo cambia lo que se ve

    def _texto_valor(self, campo, valor):
        if isinstance(campo, Opciones):
            t = campo.opciones.get(valor, valor)
            return t[0] if isinstance(t, tuple) else str(t)
        return str(valor)

    def _resumen_avanzados(self):
        """Lo que está activo (distinto de su valor por defecto) dentro de «Más opciones»: «Invertir, Conicidad: 5 deg»."""
        partes = []
        for c in self.campos:
            if not c.avanzado or isinstance(c, (Seleccion, Info, Personalizado)) or not self._visible(c):
                continue
            valor = self.valores.get(c.clave)
            if valor == c.defecto or valor in (None, "", []):
                continue
            partes.append(c.etiqueta if isinstance(c, Casilla) else f"{c.etiqueta}: {self._texto_valor(c, valor)}")
        return ", ".join(partes)

    # ------------------------------------------------------------ valores
    def ajustar_alto(self, disponible):
        """B-105: si el panel no entra en el visor, achica el cuerpo con barra; el pie nunca se tapa. B-113: el cuerpo crece
        o se achica con los campos que un cambio de modo muestra u oculta (el alto natural sale del contenido, no del
        alto que dejó la vez anterior)."""
        natural = self.desplazador.widget().sizeHint().height() + 2 * self.desplazador.frameWidth()
        otros = self.height() - self.desplazador.height()
        self.desplazador.setFixedHeight(max(40, min(natural, disponible - otros)))
        self.adjustSize()

    def _visible(self, campo):
        return campo.visible_si is None or bool(campo.visible_si(self.valores))

    def _a_la_vista(self, campo):
        """Visible, en la pestaña elegida y no escondido en una sección cerrada: la selección no salta sola a un campo que
        la persona no ve."""
        if not self._visible(campo) or campo.pestana != self._pestana_actual():
            return False
        if campo.seccion and not self.plegables[campo.seccion].abierta:
            return False
        return not campo.avanzado or campo.pestana is not None or self.seccion is None or self.seccion.abierta

    def _refrescar_vivas(self):
        for c in self.campos:
            if not isinstance(c, OpcionesVivas):
                continue
            w, nuevas = self.widgets[c.clave], c.listar(self.valores)
            w.blockSignals(True)
            if nuevas != c.opciones:
                c.opciones = nuevas
                w.clear()
                for k, texto in nuevas.items():
                    if isinstance(texto, tuple):
                        w.addItem(icono(texto[1]), texto[0], k)
                    else:
                        w.addItem(texto, k)
            w.setCurrentIndex(max(w.findData(self.valores.get(c.clave)), 0))
            self.valores[c.clave] = w.currentData()
            w.blockSignals(False)

    def _actualizar_visibles(self):
        self._refrescar_vivas()
        for c in self.campos:
            vis = self._visible(c) and not getattr(c, "oculta", False)
            self.widgets[c.clave].setVisible(vis)
            if not getattr(c, "ancho_completo", False):
                self.etiquetas[c.clave].setVisible(vis)
            if c.etiqueta_si is not None:
                texto = c.etiqueta_si(self.valores)
                if texto != self.etiquetas[c.clave].text():
                    self.etiquetas[c.clave].setText(texto)
        for rotulo, claves in self.rotulos:
            rotulo.setVisible(any(self._visible(self._por_clave[k]) for k in claves))
        if self.seccion is not None:
            self.seccion.setVisible(any(self._visible(c) for c in self.campos if c.avanzado and not c.pestana))
            self.seccion.set_resumen(self._resumen_avanzados())
        for titulo, s in self.plegables.items():
            s.setVisible(any(self._visible(c) for c in self.campos if c.seccion == titulo))
        self._actualizar_titulo()
        invalido = self._validar_expresiones()
        if invalido is not None and invalido.avanzado and self.seccion is not None and not self.seccion.abierta:
            self.seccion.boton.setChecked(True)          # un valor inválido no se queda escondido en «Más opciones» cerrada
        self._revisar_selecciones_visibles()
        if self.activa is not None and self.activa.filtros_si and self._filtros(self.activa) != self.visor.filtro:
            self._activar(self.activa)              # B-265: el modo cambia qué se elige en la vista
        self._reubicar()          # B-113: si el cambio de modo mostró u ocultó campos, el panel crece o se achica

    def _revisar_selecciones_visibles(self):
        """Al cambiar de modo, las selecciones de campos que dejan de verse dejan de resaltarse en la vista (se conservan
        por si se vuelve al modo anterior) y, si el campo activo se ocultó, la selección pasa al siguiente que falta."""
        visibles = tuple(c.clave for c in self.campos if isinstance(c, Seleccion) and self._visible(c))
        if visibles == getattr(self, "_sel_visibles", visibles):
            self._sel_visibles = visibles
            return
        self._sel_visibles = visibles
        if self.activa is not None and self.activa.clave not in visibles:
            self._activar(next((self._por_clave[k] for k in visibles
                                if not self.valores.get(k) and self._a_la_vista(self._por_clave[k])), None))
        self._refrescar_seleccion()

    def _validar_expresiones(self):
        """Marca en rojo las expresiones inválidas (con el motivo en su tooltip). Devuelve la primera, para llevar a ella."""
        primera = None
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
                    primera = primera or c
        return primera

    def _mostrar_campo_invalido(self):
        """El mensaje de un valor inválido y su campo quedan juntos: se lleva la vista hasta él."""
        c = self._validar_expresiones()
        enfocado = QApplication.focusWidget()
        if c is not None and not (enfocado is not None and self.desplazador.isAncestorOf(enfocado)):   # tecleando en otro campo, la vista no salta
            self.desplazador.ensureWidgetVisible(self.widgets[c.clave])

    def _cambiar(self, clave, valor):
        if registro_uso.activo is not None:
            self._uso_cambios += 1
            self._uso_cambio = time.perf_counter()
        self.valores[clave] = valor
        self._registrar_uso("comando_editado")
        self._actualizar_visibles()
        self.comando.al_cambiar(self, clave)
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
        elif isinstance(w, (QComboBox, _FilaBotones)):
            w.setCurrentIndex(max(w.findData(valor), 0))
        elif isinstance(w, (QCheckBox, QToolButton)):
            w.setChecked(bool(valor))
        elif isinstance(w, QSpinBox):
            w.setValue(int(valor))
        elif isinstance(campo, (Porcentaje, Deslizador)):
            w.numero.setValue(valor)
        elif isinstance(campo, DosTopes):
            w.poner(valor)
        self.valores[clave] = valor if not isinstance(campo, Seleccion) else list(valor)
        self._actualizar_visibles()
        self.comando.al_cambiar(self, clave)
        self._programar()

    def set_valores(self, nuevos):
        """Cambia varios valores de una vez sin una vista previa por cada uno (al pasar de una fila de una lista a otra):
        los widgets se actualizan sin avisar y al final se recalcula todo una sola vez."""
        for clave, valor in nuevos.items():
            campo = next((c for c in self.campos if c.clave == clave), None)
            w = self.widgets.get(clave)
            self.valores[clave] = list(valor) if isinstance(campo, Seleccion) else valor
            if w is None or isinstance(campo, (Seleccion, Personalizado, Info)):
                continue
            if isinstance(campo, Deslizador):
                w.numero.setValue(valor)
                continue
            if isinstance(campo, DosTopes):
                w.poner(valor)
                continue
            w.blockSignals(True)
            try:
                if isinstance(w, QLineEdit):
                    w.setText(str(valor))
                elif isinstance(w, (QComboBox, _FilaBotones)):
                    w.setCurrentIndex(max(w.findData(valor), 0))
                elif isinstance(w, (QCheckBox, QToolButton)):
                    w.setChecked(bool(valor))
                elif isinstance(w, QSpinBox):
                    w.setValue(int(valor))
            finally:
                w.blockSignals(False)
        self._refrescar_seleccion()
        self._actualizar_visibles()
        self._programar()

    # ------------------------------------------------------------ selección en la vista
    def _activar(self, campo):
        self.activa = campo
        self._pintar_filas()
        self.visor.set_filtro(self._filtros(campo) if campo is not None else None)
        # H-72: en un campo de varias caras o cuerpos, arrastrar en la vista elige con una ventana (como Fusion)
        self.visor.ventana_en_comando = bool(campo is not None and campo.maximo != 1
                                             and set(campo.filtros) & {"cara", "cuerpo", "perfil"})   # B-268
        # en un campo de varios perfiles, tocar una letra elige el texto entero (como Fusion)
        self.visor.texto_entero = bool(campo is not None and campo.maximo is None and "perfil" in campo.filtros)

    def _filtros(self, campo):
        return set(campo.filtros_si(self.valores)) if campo.filtros_si else campo.filtros

    def _pintar_filas(self):
        """Cada fila de selección dice QUÉ tiene (nombre y rasgo de lo elegido) o qué espera (Elegir cara o arista)."""
        for clave, fila in self.filas_sel.items():
            campo, hits = self._por_clave[clave], self.valores.get(clave) or []
            try:
                texto, detalle = describir_seleccion(hits, self.ctx)
                items = [describir_ref(h["ref"], self.ctx) for h in hits]
            except Exception:  # noqa: BLE001 — una referencia que no se puede nombrar no tumba el panel
                texto, detalle, items = (f"{len(hits)} seleccionado(s)" if hits else ""), "", []
            vacio = texto_filtros(campo.filtros, campo.maximo != 1)
            fila.set_estado(len(hits), self.activa is not None and clave == self.activa.clave, texto, detalle, vacio, items)

    def _quitar(self, campo, i):
        """Quita una sola referencia de un campo con varias (menú ▾ de la fila)."""
        lista = list(self.valores.get(campo.clave) or [])
        if 0 <= i < len(lista):
            del lista[i]
            self.valores[campo.clave] = lista
            self._refrescar_seleccion()
            self._actualizar_visibles()
            self.comando.al_cambiar(self, campo.clave)
            self._programar()

    def _reordenar(self, campo, i, j):
        """Sube o baja una fila de una `ListaSeleccion`: el orden de los perfiles es el de la solevación."""
        lista = list(self.valores.get(campo.clave) or [])
        if 0 <= j < len(lista):
            lista[i], lista[j] = lista[j], lista[i]
            self.valores[campo.clave] = lista
            self._refrescar_seleccion()
            self.filas_sel[campo.clave].tabla.selectRow(j)
            self._actualizar_visibles()
            self.comando.al_cambiar(self, campo.clave)
            self._programar()

    def _limpiar(self, campo):
        self.valores[campo.clave] = []
        self._refrescar_seleccion()
        self._activar(campo)
        self.comando.al_cambiar(self, campo.clave)
        self._programar()

    def elegir_boceto(self, op_id):
        """Un boceto elegido en el navegador o el timeline entra entero a un campo de perfiles, con el texto y sin los
        huecos de sus letras (Fusion: Extrude reference, Profiles). False si el campo activo no lo toma."""
        from ..nucleo.perfiles import perfiles_de_boceto
        from ..timeline.operaciones import OpExtrusion
        campo, br = self.activa, self.ctx.estado.bocetos.get(op_id)
        if campo is None or br is None or "perfil" not in campo.filtros or campo.maximo is not None:
            return False
        hits = [hit_desde_ref({"tipo": "perfil", "boceto": op_id, **OpExtrusion.referencia_perfil(p)}, self.ctx.estado)
                for p in perfiles_de_boceto(br)]
        if hits:                     # si falta alguno entra todo; si ya estaban todos, sale
            faltante = next((h for h in hits if all(x["ref"] != h["ref"] for x in self.valores.get(campo.clave) or [])), hits[0])
            self._elegida(faltante, hits)
        return bool(hits)

    def elegir_varias(self, hits):
        """Selección en ventana dentro del comando (H-72): suma al campo activo lo que acepta y todavía no tiene."""
        campo = self.activa
        if campo is None:
            return
        tiene = [h["ref"] for h in self.valores.get(campo.clave) or []]
        nuevos = [h for h in hits if acepta(self._filtros(campo), h) and h["ref"] not in tiene]
        if campo.maximo is not None:                  # un campo de 1 o 2 no recibe más de lo que admite
            nuevos = nuevos[:max(0, campo.maximo - len(tiene))]
        if nuevos:
            self._elegida(nuevos[0], grupo=nuevos)

    def _elegida(self, hit, grupo=None):
        campo = self.activa
        if campo is None or not self.isVisible():
            return
        try:
            hit = self.comando.ajustar_hit(campo, hit, self.ctx, self.visor) or hit
        except Exception:  # noqa: BLE001 — sin el ajuste, vale lo que se tocó
            pass
        lista = list(self.valores.get(campo.clave) or [])
        repetida = next((h for h in lista if h["ref"] == hit["ref"]), None)
        destino = campo.desvio(self.valores, hit, self.ctx) if campo.desvio and grupo is None and repetida is None else None
        if destino is not None:
            clave, otros = destino
            tenia = self.valores.get(clave) or []
            quedan = [h for h in tenia if h["ref"] != hit["ref"]]
            self.set_valores(dict(otros, **{clave: [hit]}) if len(quedan) == len(tenia) else {clave: quedan})
            self.comando.al_cambiar(self, clave)
            return
        if grupo is None and "perfil" in campo.filtros:
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
        self.comando.al_cambiar(self, campo.clave)
        self.comando.al_elegir(self, campo.clave)
        self._programar()

    def _siguiente_seleccion(self, campo):
        sels = [c for c in self.campos if isinstance(c, Seleccion) and self._a_la_vista(c)]
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
            if isinstance(c, Seleccion) and self._visible(c) and not c.sin_resalte:
                for h in self.valores.get(c.clave) or []:
                    prims.extend(h.get("dibujo") or [])
        self.visor.set_capa("seleccion", prims)
        self._pintar_filas()
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
    def _limpiar_mensaje(self):
        """Cambió un valor o una selección: el aviso de antes ya no vale y se va al instante, sin esperar a la previa
        (que lo vuelve a mostrar si sigue siendo cierto). El «Calculando…» de la previa aparte se queda."""
        if self.mensaje.text() and self.mensaje.property("tipo") != "calculando":
            self.mensaje.setText("")
            self.mensaje.setVisible(False)
            self.icono_mensaje.setVisible(False)
            self._reubicar()

    def _programar(self):
        self._limpiar_mensaje()
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
            except ErrorComando as e:
                self._mostrar(str(e), tipo="instruccion")
            except ErrorExpresion as e:
                self._mostrar(str(e), tipo="invalido")
                self._mostrar_campo_invalido()
            except Exception as e:  # noqa: BLE001 — el análisis que falla se informa, no tumba la app
                self._mostrar(f"⚠ {e}", tipo="error")
            self._previa_ok = True
            return
        try:
            op = self.comando.construir(self.valores, self.ctx)
        except (ErrorComando, ErrorExpresion) as e:
            self._cancelar_previa_hijo()
            self.ultima_op = None
            self._mostrar(str(e), tipo="instruccion" if isinstance(e, ErrorComando) else "invalido")
            if isinstance(e, ErrorExpresion):
                self._mostrar_campo_invalido()
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
            from ..nucleo import geometria as geo
            with geo.en_serie():         # B-293
                estado, avisos = self.ctx.doc.previsualizar(op, self.ctx.indice, en_vivo=self._previa_aislada)
            self._previa_aislada = True
        except Exception as e:  # noqa: BLE001 — se muestra el error del kernel como en Fusion
            self._mostrar(f"⚠ {e}", tipo="error")
            self._previa_vista(None)
            self.previa.emit(None)
            return
        self._previa_ok = True
        self._mostrar(" ".join(avisos), tipo="aviso")
        self._previa_vista(op)
        self._previa_lista(estado)

    def _previa_lista(self, estado):
        self.visor.cuerpos_de_previa = frozenset(estado.cuerpos) - frozenset(self.ctx.estado.cuerpos)
        self.previa.emit(estado)
        try:
            self.comando.analizar_previa(self.valores, self.ctx, estado, self.visor)
        except Exception as e:  # noqa: BLE001 — el análisis que falla se informa, no tumba la vista previa
            self._mostrar(f"⚠ {e}", tipo="aviso")
        self._avisar_previa(estado)

    def _avisar_previa(self, estado):
        try:
            self.comando.previa_lista(self, estado)
        except Exception as e:  # noqa: BLE001 — si el ajuste falla, la previa sigue sirviendo
            self._mostrar(f"⚠ {e}", tipo="aviso")

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
        if not arrastrando:
            return False    # el valor tecleado y el asa al soltarse salen del kernel exacto; P-99: la plantilla (otra
            # extrusión y su malla: 1 s con 29 perfiles) se arma al primer arrastre, no en cada clic que suma un perfil
        variables = {"distancia", "distancia2", "direccion", "medida", "simetrica", "invertir"}
        firma = (self.ctx.estado, repr({k: v for k, v in p.items() if k not in variables}),
                 self.visor.config.teselado, self.visor.config.angular)
        if self._prisma_previa is None or self._prisma_previa[0] != firma:
            plano, _ = op._caras(self.ctx.estado, Contexto(self.ctx.doc.parametros.valores()))
            unidad = type(op)(op.id, op.nombre, **dict(p, distancia="1 mm", direccion="un_lado", simetrica=False,
                                                      invertir=False))
            with geo.en_serie():         # B-293
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
        d1 = self.ctx.evaluar(p["distancia"])
        modo = "simetrica" if p.get("simetrica") else p["direccion"]
        medida = "total" if p.get("simetrica") else p["medida"]
        d2 = self.ctx.evaluar(p["distancia2"]) if modo == "dos_lados" else None
        geo.exigir_distancias_extrusion(modo, d1, d2, medida)
        a, b = tramo_previa(modo, d1, d2, medida, p.get("invertir"))
        _, estado, prismas = self._prisma_previa
        mallas = {cid: prisma.transformar(a, b) for cid, prisma in prismas.items()}
        estado._mallas_previa = mallas
        estado._cajas_previa = {cid: prisma.caja(a, b) for cid, prisma in prismas.items()}
        for cid, (v, _, _) in mallas.items():
            estado.cuerpos[cid].forma.vertices = v
        if self.visor._estado is not estado:
            self._previa_lista(estado)
        else:
            self.visor.actualizar_prismas(estado, mallas)
            self._avisar_previa(estado)
        self._previa_ok = True
        if self.mensaje.text():
            self._mostrar("")
        return True

    def _previa_pesada(self, op):
        if op.TIPO not in TIPOS_PESADOS or self.ctx.doc.motor != "opencascade":
            return False
        from ..nucleo import geometria as geo
        cuerpos = [self.ctx.estado.cuerpos.get(cid) for cid in _ids_cuerpo(op.p)]   # un id que ya no existe lo informa el camino normal
        # B-306/B-341: desfasar o engrosar una cara libre (el filete de una rosca) tarda de segundos a minutos
        if op.TIPO in ("desfase_cara", "engrosar", "sup_desfase"):
            from ..nucleo.referencias import cara_libre
            if any(c is not None and any(map(cara_libre, geo.caras(c.forma))) for c in cuerpos):
                return True
        return any(c is not None and len(geo.caras(c.forma)) >= CARAS_PESADAS for c in cuerpos)

    def _iniciar_previa(self, op):
        from ..nucleo.aislado import CalculoPendiente, TareaAislada
        try:
            self._hijo_previa = CalculoPendiente("previa_visual", {
                "receta": self.ctx.doc.a_dict(), "operacion": op.a_dict(), "indice": self.ctx.indice,
                "deflexion": self.visor.config.teselado or 0.05, "angular": self.visor.config.angular})
            self._op_hijo = op
            self._t_hijo.start()
            self._mostrar("Calculando vista previa en un proceso aparte…", tipo="calculando")
        except TareaAislada as e:
            self._mostrar(str(e), tipo="aviso")

    def _recibir_previa(self):
        from ..nucleo.aislado import FalloDelCalculo
        from ..timeline.calculo_aislado import leer_previa_visual
        try:
            salida = self._hijo_previa.sondear()
            if salida is None:
                self._cortar_previa_vieja()
                return
            estado, avisos = leer_previa_visual(salida, self.ctx.estado)
            self._previa_ok = self.ultima_op is not None and self.ultima_op.a_dict() == self._op_hijo.a_dict()
            self._mostrar(" ".join(avisos), tipo="aviso")
            if self._previa_ok:
                self._previa_vista(self._op_hijo)
            self._previa_lista(estado)
        except Exception as e:  # noqa: BLE001 — un hijo caído o vencido: la previa se apaga y el documento queda intacto
            self._previa_ok = False
            # B-306: si el cálculo ya falló con estos valores, Aceptar no lo repite en la ventana (tardaría lo mismo).
            if isinstance(e, FalloDelCalculo) and self.ultima_op is not None:
                self._previa_aparte = self.ultima_op.a_dict() != self._op_hijo.a_dict()
            self._mostrar(f"⚠ {e}", tipo="error")
            self.previa.emit(None)
        self._t_hijo.stop()
        self._hijo_previa = None
        self._previa_cortada = False
        pendiente, self._pendiente_hijo = self._pendiente_hijo, None
        if pendiente is not None and pendiente.a_dict() != self._op_hijo.a_dict():
            self._iniciar_previa(pendiente)

    def _cortar_previa_vieja(self):
        """Un valor nuevo no espera a un cálculo que se alarga. Un corte por respuesta: rehacer el documento también tarda."""
        from ..nucleo import aislado
        pendiente = self._pendiente_hijo
        if (pendiente is None or self._previa_cortada
                or time.monotonic() - self._hijo_previa.inicio < aislado.PACIENCIA_PREVIA):
            return
        self._hijo_previa.cancelar(ya=True)
        self._hijo_previa = None
        self._previa_cortada = True
        self._cancelar_previa_hijo()
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

    def _mostrar(self, texto, aviso=False, tipo=None):
        """Estado del panel. `tipo`: instruccion (falta elegir algo), invalido (valor mal escrito), aviso, calculando o error;
        sin `tipo`, `aviso=True` es un aviso y lo demás un error. El símbolo acompaña al color."""
        tipo = tipo or ("aviso" if aviso else "error")
        if registro_uso.activo is not None and texto and texto != self._uso_error:
            if tipo in ("error", "invalido"):
                registrar_error(origen="comando", comando=self.comando.CLAVE, mensaje=texto)
                registro_uso.activo.emitir("comando_resultado", {"comando": self.comando.CLAVE, "exito": False})
            else:                           # aviso, calculando e instrucción no son fallas (B-332)
                registrar_aviso(origen="comando", comando=self.comando.CLAVE, mensaje=texto)
        self._uso_error = texto
        poner_mensaje(self.icono_mensaje, self.mensaje, texto, tipo)
        self._reubicar()                       # el mensaje puede agrandar el panel: que siga entrando en el visor

    # ------------------------------------------------------------ cierre
    def aceptar(self):
        for _ in range(3):              # la previa puede ajustar un valor (Extruir pasa a Cortar) y pedir otra
            if not self._t_previa.isActive():
                break
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

    def _abrir_info(self):
        """El panel de información del comando: cerrarlo no cancela el comando; se va con él."""
        from .panel_info import PanelInfo
        if getattr(self.comando, "info", None) is None:
            self.comando.info = PanelInfo(self.parent() or self.visor, **self.comando.INFO)
        self.comando.info.show()
        self.comando.info.ubicar_informacion()

    def _cerrar(self):
        self.cerrando = True
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
        if self.comando.INFO and getattr(self.comando, "info", None) is not None:
            self.comando.info.deleteLater()
            self.comando.info = None
        self.comando.al_cerrar(self.ctx)
        self.previa.emit(None)
        self.hide()

    def _enter_es_del_control(self):
        """Enter lo atiende el control con foco (lista abierta de un desplegable, tabla, texto de varias líneas, botón)
        en vez de aceptar el comando por accidente. Devuelve True si ya lo resolvió."""
        w = QApplication.focusWidget()
        if isinstance(w, QComboBox) and w.view().isVisible() or isinstance(w, (QAbstractItemView, QPlainTextEdit)):
            return True
        if w is not None and w in (self.boton_cancelar, self.boton_preajustes):
            w.click()                       # Enter sobre «Cancelar» cancela y sobre «⋯» abre el menú (no aceptan); sobre cualquier otro botón sigue aceptando
            return True
        return False

    def keyPressEvent(self, e):
        if e.key() in (Qt.Key_Return, Qt.Key_Enter):
            if not self._enter_es_del_control():
                self.aceptar()
        elif e.key() == Qt.Key_Escape:
            self.cancelar()
        else:
            super().keyPressEvent(e)
