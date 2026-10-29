# -*- coding: utf-8 -*-
"""
Preferencias del usuario (persistentes con QSettings) y su diálogo, con la misma organización
que el de Fusion 360: árbol de categorías a la izquierda, una línea de descripción arriba,
filas "etiqueta: control" y los botones Restablecer / Aplicar / Aceptar / Cancelar.

Solo se ofrecen opciones que OmniCAD cumple de verdad. Las categorías de Fusion que
dependen de la nube o de licencias (Tokens, Red, Recopilación de datos…) no se copian.
"""
import subprocess
import threading

from PySide6.QtCore import QSettings, QSize, Qt, QUrl, Signal
from PySide6.QtGui import QDesktopServices, QFontDatabase
from PySide6.QtWidgets import (QCheckBox, QComboBox, QDialog, QDoubleSpinBox, QFormLayout, QFrame, QHBoxLayout,
                               QLabel, QLineEdit, QPlainTextEdit, QPushButton, QScrollArea, QSlider,
                               QSpinBox, QStackedWidget, QToolButton, QTreeWidget, QTreeWidgetItem, QVBoxLayout, QWidget)

from .. import NOMBRE_APP
from ..asistente import config as config_asistente
from ..asistente import modelos
from ..asistente.proveedores.agente_local import AGENTES, AgenteLocal, ejecutable
from ..asistente.proveedores.base import ErrorProveedor
from ..nucleo import motor
from ..timeline.documento import TOPE_INSTRUCCIONES
from . import temas

NOMBRE_ANTERIOR = "FusionClone"      # nombre del programa hasta el 2026-10-09: sus preferencias se migran una vez

DEFECTOS = {
    "geometria/motor": "opencascade",
    "general/tema": temas.DEFECTO,            # ui/temas.py: oscuro_moderno, claro_moderno, … o usuario:<archivo>
    # Apariencia (Preferencias › Apariencia): tipografía y colores de texto por encima del tema elegido
    "interfaz/fuente": "Segoe UI",            # vacío no vale: siempre hay una fuente para la interfaz
    "interfaz/tamano_pct": 100,               # 80 a 150, de a 5: 100 es el 9pt de siempre
    "interfaz/perfil": "personalizado",       # normal, lectura_comoda o personalizado (ver PERFILES)
    "interfaz/color_texto": "",               # vacío = el del tema; '#rrggbb' lo pisa (si conserva el contraste)
    "interfaz/color_texto_tenue": "",
    "interfaz/color_acento": "",
    "boceto/fuente_cotas": "",                # vacío = la fuente de la interfaz
    "boceto/tamano_cotas_pct": 100,           # 70 a 200, de a 5: el texto de las cotas y etiquetas del boceto
    "general/raton": "fusion",               # como Fusion: medio desplaza, Mayús+medio orbita
    "general/invertir_zoom": False,
    "general/camara": "perspectiva",
    "general/tipo_orbita": "libre",
    "general/auto_mirar_boceto": True,
    "general/tamano_viewcube": "automatico",
    "general/info_herramientas": True,
    "general/autoguardado_min": 1,
    "general/puente_agentes": False,         # MCP en vivo: apagado por defecto (ui/puente.py)
    "general/puente_codigo": False,          # execute_code en vivo (corre Python en la interfaz)
    "general/registro_uso": False,           # telemetría exclusivamente local y optativa
    "navegador/no_desplegar_al_seleccionar": False,   # al elegir en el visor, no abrir ni desplazar el navegador
    # Asistente IA (ui/asistente.py), definidas en asistente/config.py › DEFECTOS. La clave de API NO se guarda acá.
    **{f"asistente/{k}": v for k, v in config_asistente.DEFECTOS.items()},
    "atajos/diseno": "extruir,empalme_3d",   # caja de herramientas (S): los que Fusion trae fijados
    "atajos/boceto": "",
    "atajos/barra": "",                      # comandos fijados en la barra de arriba (menú «Más» ⋮)
    "atajos/teclas": "{}",                   # combinaciones cambiadas por el usuario (JSON clave → combinación)
    "material/aspecto": "acero",
    "graficos/preset": "personalizar",
    "graficos/detalle": "automatico",        # teselado: automatico (según el tamaño de cada pieza), bajo, medio, alto
    "graficos/dinamico": True,               # Fusion «Dynamic»: menos efectos al navegar si baja de fps_minimo
    "graficos/fps_minimo": 30,               # Fusion «Minimum framerate during navigation (FPS)»
    "graficos/limite_fps": 0,                # 0 = sin límite; 30 o 15 ahorran batería
    "graficos/luces": "una",                 # iluminación del visor: una (la de siempre) o tres (tres puntos)
    "graficos/indicador_giro": True,         # cruz en el centro de giro mientras se orbita (como Fusion)
    "unidades/precision": 3,
    "unidades/precision_angular": 1,
    "unidades/ocultar_ceros": True,
    # efectos de lienzo: se editan en Preferencias › Gráficos y en la barra de navegación (misma clave)
    "vista/efecto_cupula": True,
    "vista/efecto_suelo": False,
    "vista/efecto_sombra_suelo": False,
    "vista/efecto_reflejo": False,
    "vista/efecto_aa": True,
    # estado de la interfaz (barra de navegación y paneles; no aparece en el diálogo)
    "vista/estilo_visual": "sombreado_aristas",
    "vista/entorno": "tema",
    "vista/rejilla": True,
    "vista/rejilla_bloqueada": False,
    "vista/forzar_rejilla": False,
    "vista/rejilla_fija": "",
    "vista/desfase_suelo": False,
    "vista/vis_planos_origen": True,
    "vista/vis_ejes_origen": True,
    "vista/vis_punto_origen": True,
    "vista/vis_planos_usuario": True,
    "vista/vis_bocetos": True,
    "vista/panel_datos": False,             # Fusion arranca con el panel de datos cerrado
    "timeline/color_componente": False,     # engranaje del timeline › «Muestra de color por componente»
}
EFECTOS = ("cupula", "suelo", "sombra_suelo", "reflejo", "aa")
# Valores predefinidos de gráficos. Fusion trae Rendimiento, Calidad y Personalizar; «Equilibrado» lo pidió el usuario
# (2026-10-09). Cada uno fija todo junto: efectos, detalle de las piezas y «Dinámico». El límite de cuadros no: es
# para ahorrar batería y lo elige cada uno. Tocar cualquiera de estas claves pasa a «Personalizar».
_EFECTOS_BASE = {"vista/efecto_cupula": True, "vista/efecto_suelo": False, "vista/efecto_sombra_suelo": False,
                 "vista/efecto_reflejo": False}
PRESETS = {
    "rendimiento": {**_EFECTOS_BASE, "vista/efecto_aa": False, "graficos/detalle": "bajo", "graficos/dinamico": True},
    "equilibrado": {**_EFECTOS_BASE, "vista/efecto_aa": True, "graficos/detalle": "automatico",
                    "graficos/dinamico": True},
    "calidad": {**_EFECTOS_BASE, "vista/efecto_suelo": True, "vista/efecto_sombra_suelo": True, "vista/efecto_aa": True,
                "graficos/detalle": "alto", "graficos/dinamico": False},
}
# Valores predefinidos de Apariencia (como PRESETS de Gráficos): elegir uno fija la tipografía y los colores juntos.
# «Lectura cómoda» deja los colores en el tema (su texto es el de mayor contraste que el tema garantiza) y sube la letra.
_APARIENCIA_BASE = {"interfaz/fuente": "Segoe UI", "interfaz/color_texto": "", "interfaz/color_texto_tenue": "",
                    "interfaz/color_acento": "", "boceto/fuente_cotas": "", "boceto/tamano_cotas_pct": 100}
PERFILES = {
    "normal": {**_APARIENCIA_BASE, "interfaz/tamano_pct": 100},
    "lectura_comoda": {**_APARIENCIA_BASE, "interfaz/tamano_pct": 120, "boceto/tamano_cotas_pct": 120},
}  # «personalizado» no fija nada: es el estado al tocar una de esas claves
# Teselado por nivel de detalle: (deflexión en mm, ángulo en radianes). Deflexión None = automática según el tamaño
# de cada pieza (ui/visor3d.deflexion_automatica). El ángulo manda en las piezas redondas: con 0.3 rad, «bajo» y
# «automático» daban los mismos 17244 triángulos en el modelo del bench (2026-10-09).
DETALLES = {"automatico": (None, 0.3), "bajo": (0.2, 0.6), "medio": (0.05, 0.3), "alto": (0.01, 0.2)}
MAX_RECIENTES = 15


def migrar_ajustes(nuevos, viejos):
    """Copia las preferencias guardadas con el nombre anterior, solo si las nuevas todavía están vacías."""
    if nuevos.allKeys() or not viejos.allKeys():
        return False
    for clave in viejos.allKeys():
        valor = viejos.value(clave)
        if clave == "general/raton" and valor == "fusionclone":
            valor = "omnicad"
        nuevos.setValue(clave, valor)
    nuevos.sync()
    return True


class Preferencias:
    """Acceso tipado a QSettings. `ajustes` permite usar un .ini temporal en las pruebas."""

    def __init__(self, ajustes=None):
        if ajustes is None:
            ajustes = QSettings(NOMBRE_APP, NOMBRE_APP)
            migrar_ajustes(ajustes, QSettings(NOMBRE_ANTERIOR, NOMBRE_ANTERIOR))
        self.q = ajustes
        motor.configurar_preferencias(self)

    def __getitem__(self, clave):
        defecto = DEFECTOS[clave]
        valor = self.q.value(clave, defecto)
        if isinstance(defecto, bool):
            return valor if isinstance(valor, bool) else str(valor).lower() in ("true", "1")
        if isinstance(defecto, (int, float)):
            try:
                return type(defecto)(valor)
            except (TypeError, ValueError):
                return defecto
        return str(valor)

    def __setitem__(self, clave, valor):
        if clave not in DEFECTOS:
            raise KeyError(clave)
        self.q.setValue(clave, valor)

    def restablecer(self):
        for clave in DEFECTOS:
            if not clave.startswith("vista/") or clave.startswith("vista/efecto_"):
                self.q.remove(clave)

    # ------------------------------------------------------------ proyectos recientes (panel de datos)
    def recientes(self):
        valor = self.q.value("recientes", [])
        if isinstance(valor, str):
            valor = [valor] if valor else []
        return [str(v) for v in valor or []]

    def agregar_reciente(self, ruta):
        lista = [r for r in self.recientes() if r.lower() != str(ruta).lower()]
        self.q.setValue("recientes", [str(ruta)] + lista[:MAX_RECIENTES - 1])

    def quitar_reciente(self, ruta):
        self.q.setValue("recientes", [r for r in self.recientes() if r.lower() != str(ruta).lower()])


# ------------------------------------------------------------------ diálogo
class CampoInstrucciones(QPlainTextEdit):
class _EtiquetaFila(QLabel):
    """Etiqueta de una fila del formulario: pide el ancho de su texto (hasta un tope) y solo parte la línea si no
    entra. Así la fila nunca queda más baja que su texto, con la letra del tamaño que sea (un QLabel con ajuste de
    línea normal da un ancho mínimo chico y una altura de una sola línea, y el texto sale cortado)."""
    TOPE = 300

    def __init__(self, texto):
        super().__init__(texto)
        self.setWordWrap(True)
        self.setAlignment(Qt.AlignRight | Qt.AlignVCenter)

    def minimumSizeHint(self):
        ancho = min(self.fontMetrics().horizontalAdvance(self.text()) + 6, self.TOPE)
        return QSize(ancho, self.heightForWidth(ancho))

    sizeHint = minimumSizeHint


    """Texto multilínea con tope de caracteres y contador debajo (`self.contador`): lo que pasa del tope (un pegado
    enorme) se corta y el contador lo dice. Instrucciones del Asistente: las propias y las de cada proyecto."""

    def __init__(self, texto="", ayuda=""):
        super().__init__(placeholderText=ayuda, tabChangesFocus=True)
        self.tope = TOPE_INSTRUCCIONES
        self.contador = QLabel(objectName="contador_instrucciones")
        temas.poner_rol(self.contador, "tenue")
        self.setMinimumHeight(80)
        self.textChanged.connect(self._contar)
        self.setPlainText(texto)

    def _contar(self):
        texto, cortado = self.toPlainText(), False
        if len(texto) > self.tope:
            cursor = self.textCursor()
            posicion = min(cursor.position(), self.tope)
            self.setPlainText(texto[:self.tope])       # vuelve a llamar a _contar, ya dentro del tope
            cursor.setPosition(posicion)
            self.setTextCursor(cursor)
            cortado = True
        self.contador.setText(f"{len(self.toPlainText())} / {self.tope} caracteres"
                              + (" · se cortó lo que sobraba" if cortado else ""))

    def texto(self):
        return self.toPlainText().strip()


def _combo(opciones, actual):
    c = QComboBox()
    for clave, texto in opciones:
        c.addItem(texto, clave)
    i = c.findData(actual)
    c.setCurrentIndex(max(i, 0))
    c.setMinimumWidth(220)
    # el ancho no lo fija el ítem más largo: con letra grande el diálogo tiene que entrar en una ventana chica
    c.setSizeAdjustPolicy(QComboBox.SizeAdjustPolicy.AdjustToMinimumContentsLengthWithIcon)
    c.setMinimumContentsLength(18)
    return c


# Fuentes de lectura fácil: si están instaladas, van primero en su grupo (no se instala ni se copia ninguna).
FACILES = ("atkinsonhyperlegible", "opendyslexic")


def _es_lectura_facil(familia):
    clave = familia.lower().replace(" ", "").replace("-", "")
    return any(nombre in clave for nombre in FACILES)


def _combo_fuentes(actual, vacio=None, familias=None):
    """Fuentes instaladas. Una guardada que ya no está se muestra igual (y queda elegida).
    Con `vacio`, el primer ítem es esa etiqueta con valor '' (p. ej. «La de la interfaz»).
    Las de lectura fácil (Atkinson Hyperlegible, OpenDyslexic) van primero, en su grupo."""
    familias = list(QFontDatabase.families()) if familias is None else list(familias)
    faciles = [f for f in familias if _es_lectura_facil(f)]
    resto = [f for f in familias if not _es_lectura_facil(f)]
    c = QComboBox()
    if vacio is not None:
        c.addItem(vacio, "")
    if actual and actual not in familias:
        c.addItem(f"{actual} (no instalada)", actual)
    if faciles:
        c.addItem("Lectura fácil", None)
        c.model().item(c.count() - 1).setEnabled(False)
        for familia in faciles:
            c.addItem(familia, familia)
        c.insertSeparator(c.count())
    for familia in resto:
        c.addItem(familia, familia)
    c.setCurrentIndex(max(c.findData(actual), 0))
    c.setMinimumWidth(220)
    c.setSizeAdjustPolicy(QComboBox.SizeAdjustPolicy.AdjustToMinimumContentsLengthWithIcon)
    c.setMinimumContentsLength(18)
    return c


class CampoColor(QWidget):
    """Color de texto de la interfaz: el del tema (vacío) o uno propio con el selector; «Quitar» vuelve al tema."""
    cambiado = Signal()

    def __init__(self, token, valor):
        super().__init__()
        self.token = token
        self._valor = temas.normalizar_color(valor) or ""
        self.boton = QPushButton(objectName="campo_color")
        self.quitar = QPushButton("Quitar", objectName="quitar_color")
        self.quitar.setToolTip("Vuelve al color del tema.")
        self.boton.clicked.connect(self._elegir)
        self.quitar.clicked.connect(lambda: self.setValue(""))
        fila = QHBoxLayout(self)
        fila.setContentsMargins(0, 0, 0, 0)
        fila.addWidget(self.boton, 1)
        fila.addWidget(self.quitar)
        self._pintar()

    def _pintar(self):
        del_tema = temas.color(self.token)
        color = self._valor or del_tema
        self.boton.setText(self._valor or f"Del tema ({del_tema})")
        self.boton.setStyleSheet(f"text-align: left; padding-left: 18px; border-left: 12px solid {color};")
        self.quitar.setEnabled(bool(self._valor))

    def refrescar(self):
        self._pintar()

    def _elegir(self):
        from PySide6.QtGui import QColor
        from PySide6.QtWidgets import QColorDialog
        color = QColorDialog.getColor(QColor(self._valor or temas.color(self.token)), self, "Color del texto")
        if color.isValid():
            self.setValue(color.name())

    def value(self):
        return self._valor

    def setValue(self, valor):
        color = temas.normalizar_color(valor) if valor else None
        color = color or ""
        if color == self._valor:
            return
        self._valor = color
        self._pintar()
        self.cambiado.emit()


# (página, padre, título en el árbol, descripción, [(clave, etiqueta, tipo, opciones)])
PAGINAS = [
    ("geometria", None, "Geometría", "Motor geométrico del documento: se recalcula entero al cambiarlo", [
        ("geometria/motor", "Motor geométrico", "combo",
         [("opencascade", "OpenCascade"), ("omnikernel", "OmniKernel")]),
        (None, "Versión de OmniKernel", "version_motor", None),
    ]),
    ("general", None, "General", "Preferencias que controlan el comportamiento general de la interfaz de usuario", [
        (None, "Idioma del usuario", "combo", [("es", "Español | Español")]),
        (None, "Orientación de modelado por defecto", "combo", [("z", "Z hacia arriba")]),
        ("general/tema", "Tema de la interfaz", "tema", None),
        (None, "Temas propios", "acciones_tema", None),
        ("general/autoguardado_min", "Intervalo de copia de seguridad de recuperación automática (minutos)", "entero", (1, 60)),
        ("general/info_herramientas", "Mostrar información de herramientas", "check", None),
        ("navegador/no_desplegar_al_seleccionar", "Al seleccionar en el visor, no desplegar el navegador "
         "(solo resaltar en amarillo dónde está)", "check", None),
        ("general/registro_uso", "Registro de uso local (14 días, hasta 50 MB; no se envía nada)", "check", None),
        ("general/raton", "Configuración del ratón (encuadre, zoom, órbita)", "combo",
         [("omnicad", "OmniCAD (izquierdo: órbita)"), ("fusion", "Fusion (Mayús + medio: órbita)"),
          ("tinkercad", "Tinkercad (derecho: órbita)")]),
        ("general/camara", "Tipo de cámara por defecto", "combo",
         [("perspectiva", "Perspectiva"), ("ortografica", "Ortográfica"),
          ("persp_orto_caras", "Perspectiva con caras ortográficas")]),
        ("general/tipo_orbita", "Tipo de órbita por defecto", "combo",
         [("libre", "Órbita libre"), ("restringida", "Órbita restringida")]),
        ("general/auto_mirar_boceto", "Mirar automáticamente el boceto al crearlo o editarlo", "check", None),
        ("general/invertir_zoom", "Invertir dirección de zoom", "check", None),
        ("general/tamano_viewcube", "Tamaño de ViewCube", "combo",
         [("pequeno", "Pequeño"), ("automatico", "Automático"), ("grande", "Grande")]),
        ("general/puente_agentes", "Permitir que agentes IA controlen OmniCAD (MCP en vivo)", "check", None),
        ("general/puente_codigo", "Permitir también execute_code en vivo (congela la app mientras corre: como mucho 100 s)",
         "check", None),
    ]),
    ("apariencia", None, "Apariencia", "Perfil, fuente, tamaño y color del texto de la interfaz y de las cotas del "
     "boceto. Se aplica al instante, sin reiniciar; un color solo se aplica si se lee bien sobre el tema", [
        ("interfaz/perfil", "Perfil de apariencia", "combo",
         [("personalizado", "Personalizado"), ("normal", "Normal"), ("lectura_comoda", "Lectura cómoda")]),
        ("interfaz/fuente", "Fuente de la interfaz", "fuente", None),
        ("interfaz/tamano_pct", "Tamaño del texto", "porcentaje", (80, 150)),
        ("interfaz/color_texto", "Color del texto", "color", None),
        ("interfaz/color_texto_tenue", "Color del texto secundario", "color", None),
        ("interfaz/color_acento", "Color de acento", "color", None),
        ("boceto/fuente_cotas", "Fuente de las cotas y etiquetas del boceto", "fuente_cotas", None),
        ("boceto/tamano_cotas_pct", "Tamaño de las cotas y etiquetas del boceto", "porcentaje", (70, 200)),
        (None, "", "aviso_apariencia", None),
        (None, "Apariencia", "acciones_apariencia", None),
    ]),
    ("material", None, "Material", "Preferencias que controlan el material y el aspecto por defecto", [
        ("material/aspecto", "Aspecto por defecto de los cuerpos", "combo",
         [("acero", "Acero - Satinado"), ("paleta", "Un color distinto por cuerpo")]),
    ]),
    ("graficos", None, "Gráficos", "Preferencias que se utilizan para controlar la visualización de gráficos", [
        ("graficos/preset", "Valor predefinido de gráficos", "combo",
         [("rendimiento", "Rendimiento"), ("equilibrado", "Equilibrado"), ("calidad", "Calidad"),
          ("personalizar", "Personalizar")]),
        ("graficos/detalle", "Nivel de detalle de las piezas", "combo",
         [("automatico", "Automático (según el tamaño de cada pieza)"), ("bajo", "Bajo (más rápido)"),
          ("medio", "Medio"), ("alto", "Alto (más fino)")]),
        ("graficos/dinamico", "Dinámico (menos efectos al girar si la vista se pone lenta)", "check", None),
        ("graficos/fps_minimo", "Velocidad mínima de cuadros al navegar (FPS)", "combo",
         [(n, str(n)) for n in (15, 20, 30, 45, 60)]),
        ("graficos/limite_fps", "Límite de cuadros por segundo", "combo",
         [(0, "Sin límite"), (60, "60"), (30, "30 (ahorro de batería)"), (15, "15 (máximo ahorro de batería)")]),
        ("graficos/luces", "Iluminación de la vista", "combo",
         [("una", "Una luz"), ("tres", "Tres puntos (principal, relleno y contorno)")]),
        ("graficos/indicador_giro", "Mostrar el centro de giro al orbitar", "check", None),
        ("vista/efecto_cupula", "Cúpula de entorno", "check", None),
        ("vista/efecto_suelo", "Plano del suelo", "check", None),
        ("vista/efecto_sombra_suelo", "Sombra en el suelo", "check", None),
        ("vista/efecto_reflejo", "Reflejo en el suelo", "check", None),
        ("vista/efecto_aa", "Anti-aliasing", "check", None),
    ]),
    ("valores", None, "Visualización de unidad y valor", "Preferencias que controlan cómo se muestran las unidades y los valores", [
        ("unidades/precision", "Precisión general", "combo",
         [(n, "0" if n == 0 else "0." + "123456"[:n]) for n in range(6)]),
        ("unidades/precision_angular", "Precisión angular", "combo",
         [(n, "0" if n == 0 else "0." + "123"[:n]) for n in range(4)]),
        ("unidades/ocultar_ceros", "Ocultar ceros finales", "check", None),
    ]),
    ("unidades", None, "Unidades por defecto", "Unidades por defecto de cada espacio de trabajo", []),
    ("diseno", "unidades", "Diseño", "Unidades por defecto del espacio de trabajo Diseño", [
        (None, "Unidad de longitud por defecto", "combo", [("mm", "Milímetro (mm)")]),
        (None, "Unidad de ángulo", "combo", [("grado", "Grado (°)")]),
    ]),
    ("asistente", None, "Asistente IA", "Con qué IA habla el Asistente. La clave de API sale de una variable de "
     "entorno: OmniCAD nunca la guarda ni la muestra", [
        ("asistente/proveedor", "Proveedor", "combo", [(k, v[0]) for k, v in config_asistente.PROVEEDORES.items()]),
        ("asistente/modelo", "Modelo", "modelo", None),
        ("asistente/base_url", "Dirección del servidor (base_url)", "texto", None),
        ("asistente/variante", "Esfuerzo (variante de OpenCode, esfuerzo de Codex)", "editable", None),
        ("asistente/ruta_claude_code", "Ruta de Claude Code", "texto", None),
        ("asistente/ruta_codex", "Ruta de Codex", "texto", None),
        ("asistente/ruta_opencode", "Ruta de OpenCode", "texto", None),
        (None, "Clave de API", "estado_clave", None),
        ("asistente/modo", "Modo por defecto", "combo",
         [("explicar", "Explicar"), ("mostrar", "Mostrar"), ("guiar", "Guiar"), ("hacer", "Hacer")]),
        ("asistente/tope_usd", "Tope de gasto por pedido (0 = sin tope)", "decimal", (0.0, 100.0)),
        ("asistente/permisos", "Permisos", "combo", [("cada_paso", "Preguntar en cada paso"),
                                                     ("una_vez", "Preguntar una vez por pedido"),
                                                     ("nunca", "No preguntar")]),
        ("asistente/imagenes", "Mandar imágenes del visor al modelo", "check", None),
        ("asistente/ver_herramientas", "Mostrar las herramientas que usa la IA", "check", None),
        ("asistente/instrucciones", "Instrucciones propias (valen para todos los chats)", "texto_largo", None),
        (None, "Conexión", "probar", None),
    ]),
]


CLAVES_GRAFICOS = tuple(clave for pagina, *_r, filas in PAGINAS if pagina == "graficos" for clave, *_x in filas if clave)
# Apariencia al instante (como Gráficos): cada cambio se escribe y se ve; Cancelar vuelve a lo que había.
CLAVES_APARIENCIA = ("interfaz/perfil", "interfaz/fuente", "interfaz/tamano_pct", "interfaz/color_texto",
                     "interfaz/color_texto_tenue", "interfaz/color_acento", "boceto/fuente_cotas",
                     "boceto/tamano_cotas_pct")


def _combo_temas(actual):
    """Combo con los temas incluidos y los del usuario."""
    lista, _avisos = temas.disponibles()
    c = _combo([(clave, nombre + (" (propio)" if propio else "")) for clave, nombre, propio in lista], actual)
    if c.findData(actual) < 0 and actual:                    # tema guardado que ya no existe: se ve, y cae al de fábrica
        c.addItem(f"{actual} (no se encuentra)", actual)
        c.setCurrentIndex(c.count() - 1)
    return c


class DialogoPreferencias(QDialog):
    aplicado = Signal()
    tema_elegido = Signal(str)         # vista previa: la clave del tema que se acaba de elegir en el combo
    apariencia_cambiada = Signal()     # vista previa: fuente o tamaño de la interfaz ya escritos en prefs
    graficos_cambiados = Signal()      # vista previa: Preferencias › Gráficos ya escritas en prefs (al instante)
    conexion_probada = Signal(str)     # Asistente IA › Probar conexión: el resultado, desde el hilo de la prueba
    modelos_listos = Signal(object, object)   # Asistente IA › Modelo: (pedido, resultado), desde el hilo que los lista

    def __init__(self, prefs, parent=None, inicial="general"):
        super().__init__(parent)
        self.setObjectName("dlg_preferencias")
        self.setWindowTitle("Preferencias")
        self.resize(1060, 680)
        self.prefs = prefs
        self.crear_proveedor = config_asistente.crear_proveedor   # los tests ponen el proveedor falso
        self._pedido_modelos = None    # Asistente IA › Modelo: el último pedido de lista (los viejos se descartan)
        self._modelos = {"modelos": [], "fabrica": "", "variantes": {}, "motivo": ""}   # la última lista que llegó
        self.modelos_listos.connect(self._modelos_listos)
        self.controles = {}            # clave → widget
        self.aviso_tema = None         # QLabel bajo el combo de temas: contraste, avisos y confirmaciones
        self.aviso_apariencia = None   # QLabel de Apariencia: colores de texto rechazados por contraste

        self.arbol = QTreeWidget()
        self.arbol.setHeaderHidden(True)
        self.arbol.setFixedWidth(min(320, round(270 * prefs["interfaz/tamano_pct"] / 100)))
        self.cabecera = QLabel(objectName="cabecera_pref", alignment=Qt.AlignCenter, wordWrap=True)
        self.pila = QStackedWidget(objectName="pagina_pref")
        self.desplazador = QScrollArea(widgetResizable=True, frameShape=QFrame.Shape.NoFrame)
        self.desplazador.setWidget(self.pila)
        items = {}
        self._items = items
        for pagina, padre, titulo, descripcion, filas in PAGINAS:
            it = QTreeWidgetItem([titulo])
            it.setData(0, Qt.UserRole, (self.pila.count(), descripcion))
            (items[padre].addChild(it) if padre else self.arbol.addTopLevelItem(it))
            items[pagina] = it
            self.pila.addWidget(self._pagina(filas, descripcion))
        self.arbol.expandAll()
        self.buscar = QLineEdit(placeholderText="Buscar en preferencias…", clearButtonEnabled=True)
        self.buscar.textChanged.connect(self._buscar)
        # Gráficos al instante: cada cambio se escribe y se ve en la vista; Cancelar vuelve a lo que había.
        self._sincronizando = False
        self._graficos_originales = {k: prefs[k] for k in CLAVES_GRAFICOS}
        for k in CLAVES_GRAFICOS:
            c = self.controles[k]
            (c.currentIndexChanged if isinstance(c, QComboBox) else c.toggled).connect(
                lambda *_a, k=k: self._grafico_cambiado(k))
        self._apariencia_originales = {k: prefs[k] for k in CLAVES_APARIENCIA}
        for k in CLAVES_APARIENCIA:
            c = self.controles[k]
            if isinstance(c, QComboBox):
                if k == "interfaz/perfil":
                    c.currentIndexChanged.connect(self._perfil_cambiado)
                else:
                    c.currentIndexChanged.connect(lambda *_a, k=k: self._apariencia_cambiada(k))
            elif isinstance(c, QSlider):
                c.valueChanged.connect(lambda *_a, k=k: self._apariencia_cambiada(k))
        self.arbol.currentItemChanged.connect(self._ir)
        self.arbol.setCurrentItem(items.get(inicial, items["general"]))    # p. ej. "valores" desde la barra de unidades

        cuerpo = QHBoxLayout()
        izq = QVBoxLayout()
        izq.addWidget(self.buscar)              # F16: buscador arriba del árbol de preferencias
        izq.addWidget(self.arbol)
        cuerpo.addLayout(izq)
        derecha = QVBoxLayout()
        derecha.addWidget(self.cabecera)
        derecha.addWidget(self.desplazador, 1)
        cuerpo.addLayout(derecha, 1)

        self.b_restablecer = QPushButton("Restablecer valores por defecto")
        self.b_aplicar = QPushButton("Aplicar")
        self.b_aceptar = QPushButton("Aceptar", objectName="boton_primario")
        self.b_cancelar = QPushButton("Cancelar")
        self.b_restablecer.clicked.connect(self._restablecer)
        self.b_aplicar.clicked.connect(self._aplicar)
        self.b_aceptar.clicked.connect(self._aceptar)
        self.b_cancelar.clicked.connect(self.reject)
        self.b_aceptar.setDefault(True)
        self.b_aplicar.setEnabled(False)
        botones = QHBoxLayout()
        botones.addWidget(self.b_restablecer)
        botones.addStretch(1)
        for b in (self.b_aplicar, self.b_aceptar, self.b_cancelar):
            botones.addWidget(b)

        lay = QVBoxLayout(self)
        lay.addLayout(cuerpo, 1)
        lay.addLayout(botones)

    def _buscar(self, texto):
        """F16 (FreeCAD 1.0: buscador dentro de Preferencias): atenua las páginas sin coincidencias y
        salta a la primera que tiene una. Busca en el título, la descripción y las etiquetas de las
        filas, sin distinguir mayúsculas."""
        t = texto.strip().lower()
        primera = None
        for pagina, _padre, titulo, descripcion, filas in PAGINAS:
            coincide = (not t or t in titulo.lower() or t in descripcion.lower()
                        or any(t in str(f[0]).lower() or t in str(f[1]).lower() for f in filas))
            self._items[pagina].setDisabled(not coincide)
            if coincide and t and primera is None:
                primera = self._items[pagina]
        if primera is not None:
            self.arbol.setCurrentItem(primera)

    def _pagina(self, filas, descripcion):
        w = QWidget()
        form = QFormLayout(w)
        form.setLabelAlignment(Qt.AlignRight | Qt.AlignVCenter)
        form.setFormAlignment(Qt.AlignHCenter | Qt.AlignTop)
        form.setHorizontalSpacing(12)
        form.setVerticalSpacing(10)
        form.setContentsMargins(20, 20, 20, 20)
        if not filas:
            form.addRow(QLabel("Elegí una subcategoría en el árbol de la izquierda.", wordWrap=True))
        for clave, etiqueta, tipo, opciones in filas:
            actual = self.prefs[clave] if clave else None
            texto = _EtiquetaFila(etiqueta)           # F3: con letra grande la etiqueta crece sin cortarse
            if tipo == "version_motor":
                form.addRow(texto, QLabel(motor.version_omnikernel() or "No instalado"))
                continue
            if tipo == "acciones_tema":
                form.addRow(texto, self._acciones_tema())
                continue
            if tipo == "acciones_apariencia":
                form.addRow(texto, self._acciones_apariencia())
                continue
            if tipo == "fuente":
                c = _combo_fuentes(actual)
                c.currentIndexChanged.connect(self._cambio)
                form.addRow(texto, c)
                self.controles[clave] = c
                continue
            if tipo == "fuente_cotas":
                c = _combo_fuentes(actual, "La de la interfaz")
                c.currentIndexChanged.connect(self._cambio)
                form.addRow(texto, c)
                self.controles[clave] = c
                continue
            if tipo == "porcentaje":
                minimo, maximo = opciones
                c = QSlider(Qt.Horizontal, minimum=minimo, maximum=maximo, singleStep=5, pageStep=10,
                            tickPosition=QSlider.TickPosition.TicksBelow, tickInterval=max(1, (maximo - minimo) // 5))
                c.setValue(int(actual))
                c.setMinimumWidth(180)
                valor = QLabel(f"{c.value()} %", objectName="valor_porcentaje", alignment=Qt.AlignRight | Qt.AlignVCenter)
                valor.setMinimumWidth(48)
                temas.poner_rol(valor, "tenue")
                c.valueChanged.connect(lambda v, l=valor: l.setText(f"{v} %"))
                c.valueChanged.connect(self._cambio)
                fila = QHBoxLayout()
                fila.addWidget(c, 1)
                fila.addWidget(valor)
                form.addRow(texto, fila)
                self.controles[clave] = c
                continue
            if tipo == "color":
                c = CampoColor(clave.split("interfaz/color_")[-1], actual)
                c.cambiado.connect(self._cambio)
                c.cambiado.connect(lambda *_a, k=clave: self._apariencia_cambiada(k))
                form.addRow(texto, c)
                self.controles[clave] = c
                continue
            if tipo == "aviso_apariencia":
                self.aviso_apariencia = QLabel(objectName="aviso_apariencia", wordWrap=True)
                temas.poner_rol(self.aviso_apariencia, "tenue")
                form.addRow(self.aviso_apariencia)
                continue
            if tipo == "tema":
                c = _combo_temas(actual)
                c.currentIndexChanged.connect(self._cambio)
                c.currentIndexChanged.connect(self._tema_cambiado)
                self.aviso_tema = QLabel(objectName="aviso_tema", wordWrap=True)
                temas.poner_rol(self.aviso_tema, "tenue")
                caja = QVBoxLayout()
                caja.addWidget(c)
                caja.addWidget(self.aviso_tema)
                form.addRow(texto, caja)
                self.controles[clave] = c
                self._mostrar_aviso_tema(c.currentData())
                continue
            if tipo == "combo":
                c = _combo(opciones, actual)
                if clave == "geometria/motor" and motor.version_omnikernel() is None:
                    c.model().item(c.findData("omnikernel")).setEnabled(False)
                c.setEnabled(len(opciones) > 1)
                c.currentIndexChanged.connect(self._cambio)
            elif tipo == "check":
                c = QCheckBox()
                c.setChecked(bool(actual))
                c.toggled.connect(self._cambio)
            elif tipo == "texto":
                c = QLineEdit(actual, clearButtonEnabled=True)
                c.setMinimumWidth(220)
                c.textChanged.connect(self._cambio)
            elif tipo in ("modelo", "editable"):     # lista de opciones, pero se puede escribir cualquier otra
                c = QComboBox(editable=True, insertPolicy=QComboBox.NoInsert, minimumWidth=220,
                              sizeAdjustPolicy=QComboBox.SizeAdjustPolicy.AdjustToMinimumContentsLengthWithIcon)
                c.setMinimumContentsLength(18)
                c.addItem("de fábrica", "")
                c.lineEdit().setPlaceholderText("de fábrica")
                c.setEditText(actual)
                c.currentTextChanged.connect(self._cambio)
                if tipo == "modelo":
                    c.currentTextChanged.connect(self._llenar_variantes)
                    self.b_modelos = QToolButton(text="↻", toolTip="Volver a pedir la lista de modelos.")
                    self.b_modelos.clicked.connect(lambda: self._pedir_modelos(refrescar=True))
                    self.estado_modelos = QLabel(objectName="estado_modelos", wordWrap=True)   # un motivo largo no ensancha
                    temas.poner_rol(self.estado_modelos, "tenue")
                    fila = QHBoxLayout()
                    for control, estirar in ((c, 3), (self.b_modelos, 0), (self.estado_modelos, 1)):
                        fila.addWidget(control, estirar)
                    form.addRow(texto, fila)
                    self.controles[clave] = c
                    continue
            elif tipo == "decimal":
                c = QDoubleSpinBox(suffix=" USD", decimals=2, singleStep=0.1)
                c.setRange(*opciones)
                c.setValue(float(actual))
                c.setFixedWidth(120)
                c.valueChanged.connect(self._cambio)
            elif tipo == "estado_clave":
                self.estado_clave = QLabel(objectName="estado_clave", wordWrap=True)
                form.addRow(texto, self.estado_clave)
                self.controles["asistente/proveedor"].currentIndexChanged.connect(self._estado_clave)
                self._estado_clave()
                continue
            elif tipo == "probar":
                form.addRow(texto, self._probar_conexion())
                continue
            elif tipo == "texto_largo":
                c = CampoInstrucciones(actual, ayuda="Por ejemplo: «Explicame paso a paso», «Todo es para imprimir en "
                                                     "PLA: paredes de 2 mm como mínimo». No pueden saltear los modos, "
                                                     "la tarjeta Aplicar ni el tope de gasto.")
                c.setMinimumWidth(220)
                c.setMaximumHeight(140)
                c.textChanged.connect(self._cambio)
                caja = QVBoxLayout()
                caja.addWidget(c)
                caja.addWidget(c.contador)
                form.addRow(texto, caja)
                self.controles[clave] = c
                continue
            else:
                c = QSpinBox()
                c.setRange(*opciones)
                c.setValue(int(actual))
                c.setFixedWidth(90)
                c.valueChanged.connect(self._cambio)
            form.addRow(texto, c)
            if clave:
                self.controles[clave] = c
        return w

    # ------------------------------------------------------------ apariencia
    def _acciones_apariencia(self):
        fila = QHBoxLayout()
        restablecer = QPushButton("Restablecer apariencia")
        restablecer.setToolTip("Vuelve la fuente y el tamaño a los valores de fábrica. El tema elegido no cambia.")
        restablecer.clicked.connect(self._restablecer_apariencia)
        fila.addWidget(restablecer)
        fila.addStretch(1)
        self.b_restablecer_apariencia = restablecer
        return fila

    def _perfil_cambiado(self, *_):
        """Elegir un perfil pone sus valores en los controles; después se escriben y se ve en el acto."""
        if self._sincronizando:
            return
        perfil = self.controles["interfaz/perfil"].currentData()
        if perfil in PERFILES:
            self._sincronizando = True
            try:
                for clave, valor in PERFILES[perfil].items():
                    self._poner(clave, valor)
            finally:
                self._sincronizando = False
        self._apariencia_cambiada()

    def _apariencia_cambiada(self, clave=None):
        """Vista previa como el tema: escribe las claves de Apariencia y la ventana reaplica el estilo en el acto."""
        if self._sincronizando:
            return
        if clave not in (None, "interfaz/perfil"):
            perfil = self.prefs["interfaz/perfil"]
            if perfil in PERFILES and any(self.valores()[k] != v for k, v in PERFILES[perfil].items()):
                self._sincronizando = True           # tocar una clave del perfil lo pasa a «Personalizado»
                try:
                    self._poner("interfaz/perfil", "personalizado")
                finally:
                    self._sincronizando = False
        valores = self.valores()
        for clave in CLAVES_APARIENCIA:
            self.prefs[clave] = valores[clave]
        self._mostrar_aviso_apariencia()
        self.apariencia_cambiada.emit()

    def _mostrar_aviso_apariencia(self, *_):
        """Lo que no se aplicó por contraste (o por formato), como el aviso del tema, pero en su página."""
        if self.aviso_apariencia is None:
            return
        valores = {clave.split("interfaz/color_")[-1]: self.prefs[clave]
                   for clave in CLAVES_APARIENCIA if clave.startswith("interfaz/color_")}
        base, _avisos = temas.resolver(temas.clave_activa())      # el tema sin los colores pisados
        _aplicables, rechazos = temas.colores_texto(base["colores"], valores)
        nombres = {"texto": "el texto", "texto_tenue": "el texto secundario", "acento": "el acento"}
        partes = []
        for token, valor, detalle in rechazos:
            if isinstance(detalle, str):
                partes.append(f"⚠ «{valor}» no se aplicó a {nombres[token]}: {detalle}.")
            else:
                lista = ", ".join(f"{fondo} {razon:.1f}:1" for fondo, razon in detalle[:4])
                partes.append(f"⚠ «{valor}» no se aplicó a {nombres[token]}: contraste menor a "
                              f"{temas.MIN_CONTRASTE}:1 en {lista}.")
        self.aviso_apariencia.setText("\n".join(partes) or "Los colores vacíos usan los del tema elegido.")
        temas.poner_rol(self.aviso_apariencia, "error" if rechazos else "tenue")

    def _restablecer_apariencia(self):
        self._sincronizando = True
        try:
            for clave in CLAVES_APARIENCIA:
                self._poner(clave, DEFECTOS[clave])
        finally:
            self._sincronizando = False
        self._apariencia_cambiada()
        self.b_aplicar.setEnabled(True)

    # ------------------------------------------------------------ temas
    def _acciones_tema(self):
        caja = QVBoxLayout()
        abrir = QPushButton("Abrir carpeta de temas")
        abrir.setToolTip("Los temas propios son archivos .json en esa carpeta; aparecen en la lista al reabrir "
                         "Preferencias.")
        abrir.clicked.connect(self._abrir_carpeta_temas)
        exportar = QPushButton("Exportar plantilla")
        exportar.setToolTip("Guarda el tema elegido como un .json con todos sus colores, para editarlo y hacer el tuyo.")
        exportar.clicked.connect(self._exportar_plantilla)
        for b in (abrir, exportar):          # uno debajo del otro: con letra grande entran en una ventana chica
            caja.addWidget(b, 0, Qt.AlignLeft)
        self.b_abrir_temas, self.b_exportar_tema = abrir, exportar
        return caja

    # ------------------------------------------------------------ asistente IA
    def _estado_clave(self, *_):
        """Si la variable de la clave del proveedor elegido está definida (sin mostrarla) y los valores de fábrica."""
        proveedor = self.controles["asistente/proveedor"].currentData()
        _nombre, variable, modelo, base_url = config_asistente.PROVEEDORES[proveedor]
        agente = proveedor in config_asistente.AGENTES_LOCALES
        self.controles["asistente/modelo"].lineEdit().setPlaceholderText(f"de fábrica: {modelo or 'el que use el CLI'}")
        if self.arbol.currentItem() is self._items["asistente"]:     # perezoso: solo con la página a la vista
            self._pedir_modelos()
        self.controles["asistente/base_url"].setPlaceholderText(
            "no se usa" if agente else f"de fábrica: {base_url or 'la de Anthropic'}")
        for tipo in config_asistente.AGENTES_LOCALES:     # autodetectada; lo escrito acá manda
            self.controles[f"asistente/ruta_{tipo}"].setPlaceholderText(
                ejecutable(tipo) or f"no se encuentra «{AGENTES[tipo][1]}» en el PATH")
        if agente:
            texto, rol = (f"No hace falta: usa el {AGENTES[proveedor][0]} instalado y logueado en esta PC, con tu "
                          "suscripción. OmniCAD no ve ni guarda tu cuenta; si no está logueado, abrí una terminal y "
                          f"corré «{AGENTES[proveedor][1]}».", "tenue")
        elif variable is None:
            texto, rol = "No hace falta: el servidor local no pide clave.", "tenue"
        elif config_asistente.clave_definida(proveedor):
            texto, rol = f"✓ La variable {variable} está definida.", "ok"
        else:
            texto, rol = f"✗ Falta la variable de entorno {variable}: definila y reabrí OmniCAD.", "error"
        self.estado_clave.setText(texto)
        temas.poner_rol(self.estado_clave, rol)

    def _pedir_modelos(self, refrescar=False):
        """Pide en un hilo los modelos del proveedor elegido (IA-10): el diálogo no se congela mientras el CLI o la
        API responden; si ya están en memoria, se ponen en el acto."""
        v = self.valores()
        proveedor = v["asistente/proveedor"]
        pedido = (proveedor, v.get(f"asistente/ruta_{proveedor}", ""), v["asistente/base_url"])
        self._pedido_modelos = pedido
        self.estado_modelos.setText("cargando modelos…")
        temas.poner_rol(self.estado_modelos, "tenue")
        self.b_modelos.setEnabled(False)

        def listar():
            resultado = modelos.modelos_disponibles(*pedido, refrescar=refrescar)
            try:
                self.modelos_listos.emit(pedido, resultado)
            except RuntimeError:                 # se cerró Preferencias mientras listaba
                pass

        threading.Thread(target=listar, daemon=True, name="modelos").start()

    def _modelos_listos(self, pedido, resultado):
        if pedido != self._pedido_modelos:       # llegó la lista de un proveedor que ya no está elegido
            return
        self.b_modelos.setEnabled(True)
        self._modelos = resultado
        c = self.controles["asistente/modelo"]
        texto = c.currentText()
        c.blockSignals(True)                     # llenar la lista no es un cambio de la persona (Aplicar no se prende)
        c.clear()
        c.addItem(f"de fábrica: {resultado['fabrica'] or 'el que use el CLI'}", "")
        c.lineEdit().setPlaceholderText(c.itemText(0))      # Codex: el de su config, que recién ahora se sabe
        for m in resultado["modelos"]:
            c.addItem(m, m)
        c.setEditText(texto)
        c.blockSignals(False)
        n = len(resultado["modelos"])
        self.estado_modelos.setText(f"✗ {resultado['motivo']}" if not n and resultado["motivo"] else f"{n} modelos")
        temas.poner_rol(self.estado_modelos, "error" if not n and resultado["motivo"] else "tenue")
        self._llenar_variantes()

    def _llenar_variantes(self, *_):
        """Esfuerzos del modelo elegido (o del de fábrica), si el proveedor los informa (OpenCode, Codex)."""
        resultado = self._modelos
        modelo = self.valores()["asistente/modelo"] or resultado["fabrica"].split(" · ")[0]
        c = self.controles["asistente/variante"]
        texto = c.currentText()
        c.blockSignals(True)
        c.clear()
        c.addItem("de fábrica", "")
        for variante in resultado["variantes"].get(modelo) or []:
            c.addItem(variante, variante)
        c.setEditText(texto)
        c.blockSignals(False)

    def _probar_conexion(self):
        fila = QHBoxLayout()
        self.b_probar = QPushButton("Probar conexión")
        self.b_probar.setToolTip("Manda un pedido mínimo al proveedor con los valores de esta página (gasta unos "
                                 "pocos tokens).")
        self.b_probar.clicked.connect(self.probar_conexion)
        self.resultado_conexion = QLabel(objectName="resultado_conexion", wordWrap=True)
        self.conexion_probada.connect(self._conexion_probada)
        fila.addWidget(self.b_probar)
        fila.addWidget(self.resultado_conexion, 1)
        return fila

    def probar_conexion(self):
        """Pide «OK» al modelo en un hilo aparte (la red no congela el diálogo)."""
        v = self.valores()
        try:
            proveedor = self.crear_proveedor({k: v[f"asistente/{k}"] for k in config_asistente.CLAVES})
        except ErrorProveedor as e:
            self._conexion_probada(f"✗ {e}")
            return
        self.b_probar.setEnabled(False)
        self.resultado_conexion.setText("Probando…")
        temas.poner_rol(self.resultado_conexion, "tenue")

        def probar():
            if isinstance(proveedor, AgenteLocal):   # sin gastar cupo: que esté instalado (el login lo dice el pedido)
                try:
                    version = proveedor.version()
                except (OSError, subprocess.SubprocessError) as e:
                    version, error = None, e
                else:
                    error = "no respondió a --version"
                self.conexion_probada.emit(f"✓ Encontrado: {version} ({proveedor.ruta})." if version else
                                           f"✗ {proveedor.nombre} ({proveedor.ruta}) {error}.")
                return
            try:
                r = proveedor.responder("", [{"rol": "usuario", "contenido": [
                    {"tipo": "texto", "texto": "Respondé solo OK."}]}], [])
                self.conexion_probada.emit(f"✓ Conectó: el modelo respondió «{r.texto.strip()[:40]}».")
            except Exception as e:  # noqa: BLE001 — ErrorProveedor y cualquier falla rara se muestran igual
                self.conexion_probada.emit(f"✗ {e}")

        threading.Thread(target=probar, daemon=True, name="probar_conexion").start()

    def _conexion_probada(self, texto):
        self.b_probar.setEnabled(True)
        self.resultado_conexion.setText(texto)
        temas.poner_rol(self.resultado_conexion, "ok" if texto.startswith("✓") else "error")

    def _tema_cambiado(self, *_):
        clave = self.controles["general/tema"].currentData()
        self._mostrar_aviso_tema(clave)
        for control in self.controles.values():
            if isinstance(control, CampoColor):
                control.refrescar()                # «Del tema (…)» con los colores del tema elegido
        self._mostrar_aviso_apariencia()
        self.tema_elegido.emit(clave)

    def _mostrar_aviso_tema(self, clave, extra=""):
        """Texto bajo el combo: lo que no cierra del tema elegido (contraste, archivos ignorados) y `extra`."""
        tema, avisos = temas.resolver(clave)
        partes = [extra] if extra else ["Se aplica al instante, sin reiniciar."]
        bajos = temas.contraste_bajo(tema["colores"])
        if bajos:
            lista = ", ".join(f"{t}/{f} {r:.1f}" for t, f, r in bajos[:4])
            partes.append(f"⚠ Contraste menor a {temas.MIN_CONTRASTE}:1 en {lista}"
                          + ("…" if len(bajos) > 4 else "") + ".")
        partes += [f"⚠ {a}" for a in avisos]
        self.aviso_tema.setText("\n".join(partes))

    def _abrir_carpeta_temas(self):
        carpeta = temas.carpeta_temas(crear=True)
        QDesktopServices.openUrl(QUrl.fromLocalFile(str(carpeta)))
        return carpeta

    def _exportar_plantilla(self):
        combo = self.controles["general/tema"]
        clave = combo.currentData()
        try:
            ruta = temas.exportar_plantilla(temas.ruta_plantilla_nueva(temas.carpeta_temas(crear=True)), clave)
        except OSError as e:
            self._mostrar_aviso_tema(clave, f"⚠ No se pudo guardar la plantilla: {e.strerror or e}")
            return None
        # el combo ahora incluye el tema nuevo (sin disparar la vista previa)
        combo.blockSignals(True)
        nuevo = _combo_temas(clave)
        combo.clear()
        for i in range(nuevo.count()):
            combo.addItem(nuevo.itemText(i), nuevo.itemData(i))
        combo.setCurrentIndex(max(combo.findData(clave), 0))
        combo.blockSignals(False)
        self._mostrar_aviso_tema(clave, f"Plantilla guardada: {ruta}. Editala y reabrí Preferencias para elegirla.")
        return ruta

    def _ir(self, item, _anterior=None):
        if item is None:
            return
        indice, descripcion = item.data(0, Qt.UserRole)
        if indice is not None and self.pila.widget(indice).layout().rowCount() == 1 and item.childCount():
            item = item.child(0)                         # "Unidades por defecto" → su única subpágina
            indice, descripcion = item.data(0, Qt.UserRole)
        self.pila.setCurrentIndex(indice)
        self.cabecera.setText(descripcion)
        if item is self._items["asistente"]:
            self._pedir_modelos()

    def _cambio(self, *_):
        self.b_aplicar.setEnabled(True)

    # ------------------------------------------------------------ gráficos (al instante)
    def _poner(self, clave, valor):
        c = self.controles[clave]
        if isinstance(c, QComboBox):
            i = c.findData(valor)
            if i < 0:                               # un valor que la lista no tiene (p. ej. fuente no instalada)
                c.addItem(str(valor), valor)
                i = c.count() - 1
            c.setCurrentIndex(i)
        elif isinstance(c, (QSlider, QSpinBox, QDoubleSpinBox)):
            c.setValue(valor)
        elif isinstance(c, CampoColor):
            c.setValue(valor)
        else:
            c.setChecked(bool(valor))

    def _grafico_cambiado(self, clave):
        """Elegir un valor predefinido pone sus valores en los demás controles; tocar uno de esos controles pasa a
        «Personalizar» (como Fusion). Después se escribe todo y la vista lo muestra en el acto."""
        if self._sincronizando:
            return
        self._sincronizando = True
        try:
            valores = self.valores()
            preset = valores["graficos/preset"]
            if clave == "graficos/preset" and preset in PRESETS:
                for k, v in PRESETS[preset].items():
                    self._poner(k, v)
            elif preset in PRESETS and clave in PRESETS[preset] and valores[clave] != PRESETS[preset][clave]:
                self._poner("graficos/preset", "personalizar")
        finally:
            self._sincronizando = False
        valores = self.valores()
        for k in CLAVES_GRAFICOS:
            self.prefs[k] = valores[k]
        self.graficos_cambiados.emit()

    def reject(self):
        actuales = {k: self.prefs[k] for k in CLAVES_GRAFICOS}
        if actuales != self._graficos_originales:
            for k, v in self._graficos_originales.items():
                self.prefs[k] = v
            self.graficos_cambiados.emit()
        if {k: self.prefs[k] for k in CLAVES_APARIENCIA} != self._apariencia_originales:
            for k, v in self._apariencia_originales.items():
                self.prefs[k] = v
            self.apariencia_cambiada.emit()
        super().reject()

    def valores(self):
        salida = {}
        for clave, c in self.controles.items():
            if isinstance(c, QComboBox) and c.isEditable():   # lo escrito; «de fábrica: …» es vacío
                texto = c.currentText().strip()
                salida[clave] = c.itemData(c.findText(texto)) if c.findText(texto) >= 0 else texto
            elif isinstance(c, QComboBox):
                salida[clave] = c.currentData()
            elif isinstance(c, QCheckBox):
                salida[clave] = c.isChecked()
            elif isinstance(c, QLineEdit):
                salida[clave] = c.text().strip()
            elif isinstance(c, CampoInstrucciones):
                salida[clave] = c.texto()
            else:
                salida[clave] = c.value()
        return salida

    def _cargar(self):
        for clave, c in self.controles.items():
            valor = self.prefs[clave]
            if isinstance(c, QComboBox) and c.isEditable():
                c.setEditText(valor)
            elif isinstance(c, QComboBox):
                c.setCurrentIndex(max(c.findData(valor), 0))
            elif isinstance(c, QCheckBox):
                c.setChecked(bool(valor))
            elif isinstance(c, QLineEdit):
                c.setText(valor)
            elif isinstance(c, CampoInstrucciones):
                c.setPlainText(valor)
            elif isinstance(c, CampoColor):
                c.setValue(valor)
            elif isinstance(c, QDoubleSpinBox):
                c.setValue(float(valor))
            else:
                c.setValue(int(valor))

    def _aplicar(self):
        for clave, valor in self.valores().items():
            self.prefs[clave] = valor
        self.b_aplicar.setEnabled(False)
        self.aplicado.emit()

    def _aceptar(self):
        self._aplicar()
        self.accept()

    def _restablecer(self):
        self.prefs.restablecer()
        self._cargar()
        self.b_aplicar.setEnabled(False)
        self.aplicado.emit()
