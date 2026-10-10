# -*- coding: utf-8 -*-
"""
Preferencias del usuario (persistentes con QSettings) y su diálogo, con la misma organización
que el de Fusion 360: árbol de categorías a la izquierda, una línea de descripción arriba,
filas "etiqueta: control" y los botones Restablecer / Aplicar / Aceptar / Cancelar.

Solo se ofrecen opciones que OmniCAD cumple de verdad. Las categorías de Fusion que
dependen de la nube o de licencias (Tokens, Red, Recopilación de datos…) no se copian.
"""
from PySide6.QtCore import QSettings, Qt, QUrl, Signal
from PySide6.QtGui import QDesktopServices
from PySide6.QtWidgets import (QCheckBox, QComboBox, QDialog, QFormLayout, QHBoxLayout, QLabel, QPushButton,
                               QSpinBox, QStackedWidget, QTreeWidget, QTreeWidgetItem, QVBoxLayout, QWidget)

from .. import NOMBRE_APP
from . import iconos_tema, temas

NOMBRE_ANTERIOR = "FusionClone"      # nombre del programa hasta el 2026-10-09: sus preferencias se migran una vez

DEFECTOS = {
    "general/tema": temas.DEFECTO,            # ui/temas.py: oscuro_moderno, claro_moderno, … o usuario:<archivo>
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
    "atajos/diseno": "extruir,empalme_3d",   # caja de herramientas (S): los que Fusion trae fijados
    "atajos/boceto": "",
    "material/aspecto": "acero",
    "graficos/preset": "personalizar",
    "graficos/detalle": "automatico",        # teselado: automatico (según el tamaño de cada pieza), bajo, medio, alto
    "graficos/dinamico": True,               # Fusion «Dynamic»: menos efectos al navegar si baja de fps_minimo
    "graficos/fps_minimo": 30,               # Fusion «Minimum framerate during navigation (FPS)»
    "graficos/limite_fps": 0,                # 0 = sin límite; 30 o 15 ahorran batería
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

    def __getitem__(self, clave):
        defecto = DEFECTOS[clave]
        valor = self.q.value(clave, defecto)
        if isinstance(defecto, bool):
            return valor if isinstance(valor, bool) else str(valor).lower() in ("true", "1")
        if isinstance(defecto, int):
            try:
                return int(valor)
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
def _combo(opciones, actual):
    c = QComboBox()
    for clave, texto in opciones:
        c.addItem(texto, clave)
    i = c.findData(actual)
    c.setCurrentIndex(max(i, 0))
    c.setMinimumWidth(300)
    return c


# (página, padre, título en el árbol, descripción, [(clave, etiqueta, tipo, opciones)])
PAGINAS = [
    ("general", None, "General", "Preferencias que controlan el comportamiento general de la interfaz de usuario", [
        (None, "Idioma del usuario", "combo", [("es", "Español | Español")]),
        (None, "Orientación de modelado por defecto", "combo", [("z", "Z hacia arriba")]),
        ("general/tema", "Tema de la interfaz", "tema", None),
        (None, "Temas propios", "acciones_tema", None),
        ("general/autoguardado_min", "Intervalo de copia de seguridad de recuperación automática (minutos)", "entero", (1, 60)),
        ("general/info_herramientas", "Mostrar información de herramientas", "check", None),
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
]


CLAVES_GRAFICOS = tuple(clave for pagina, *_r, filas in PAGINAS if pagina == "graficos" for clave, *_x in filas if clave)


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
    graficos_cambiados = Signal()      # vista previa: Preferencias › Gráficos ya escritas en prefs (al instante)

    def __init__(self, prefs, parent=None, inicial="general"):
        super().__init__(parent)
        self.setObjectName("dlg_preferencias")
        self.setWindowTitle("Preferencias")
        self.resize(1060, 680)
        self.prefs = prefs
        self.controles = {}            # clave → widget
        self.aviso_tema = None         # QLabel bajo el combo de temas: contraste, avisos y confirmaciones

        self.arbol = QTreeWidget()
        self.arbol.setHeaderHidden(True)
        self.arbol.setFixedWidth(270)
        self.cabecera = QLabel(objectName="cabecera_pref", alignment=Qt.AlignCenter)
        self.pila = QStackedWidget(objectName="pagina_pref")
        items = {}
        for pagina, padre, titulo, descripcion, filas in PAGINAS:
            it = QTreeWidgetItem([titulo])
            it.setData(0, Qt.UserRole, (self.pila.count(), descripcion))
            (items[padre].addChild(it) if padre else self.arbol.addTopLevelItem(it))
            items[pagina] = it
            self.pila.addWidget(self._pagina(filas, descripcion))
        self.arbol.expandAll()
        # Gráficos al instante: cada cambio se escribe y se ve en la vista; Cancelar vuelve a lo que había.
        self._sincronizando = False
        self._graficos_originales = {k: prefs[k] for k in CLAVES_GRAFICOS}
        for k in CLAVES_GRAFICOS:
            c = self.controles[k]
            (c.currentIndexChanged if isinstance(c, QComboBox) else c.toggled).connect(
                lambda *_a, k=k: self._grafico_cambiado(k))
        self.arbol.currentItemChanged.connect(self._ir)
        self.arbol.setCurrentItem(items.get(inicial, items["general"]))    # p. ej. "valores" desde la barra de unidades

        cuerpo = QHBoxLayout()
        cuerpo.addWidget(self.arbol)
        derecha = QVBoxLayout()
        derecha.addWidget(self.cabecera)
        derecha.addWidget(self.pila, 1)
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

    def _pagina(self, filas, descripcion):
        w = QWidget()
        form = QFormLayout(w)
        form.setLabelAlignment(Qt.AlignRight | Qt.AlignVCenter)
        form.setFormAlignment(Qt.AlignHCenter | Qt.AlignTop)
        form.setHorizontalSpacing(12)
        form.setVerticalSpacing(10)
        form.setContentsMargins(20, 20, 20, 20)
        if not filas:
            form.addRow(QLabel("Elegí una subcategoría en el árbol de la izquierda."))
        for clave, etiqueta, tipo, opciones in filas:
            actual = self.prefs[clave] if clave else None
            if tipo == "acciones_tema":
                form.addRow(etiqueta, self._acciones_tema())
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
                form.addRow(etiqueta, caja)
                self.controles[clave] = c
                self._mostrar_aviso_tema(c.currentData())
                continue
            if tipo == "combo":
                c = _combo(opciones, actual)
                c.setEnabled(len(opciones) > 1)
                c.currentIndexChanged.connect(self._cambio)
            elif tipo == "check":
                c = QCheckBox()
                c.setChecked(bool(actual))
                c.toggled.connect(self._cambio)
            else:
                c = QSpinBox()
                c.setRange(*opciones)
                c.setValue(int(actual))
                c.setFixedWidth(90)
                c.valueChanged.connect(self._cambio)
            form.addRow(etiqueta, c)
            if clave:
                self.controles[clave] = c
        return w

    # ------------------------------------------------------------ temas
    def _acciones_tema(self):
        fila = QHBoxLayout()
        abrir = QPushButton("Abrir carpeta de temas")
        abrir.setToolTip("Los temas propios son archivos .json en esa carpeta; aparecen en la lista al reabrir "
                         "Preferencias.")
        abrir.clicked.connect(self._abrir_carpeta_temas)
        exportar = QPushButton("Exportar tema actual como plantilla")
        exportar.setToolTip("Guarda el tema elegido como un .json con todos sus colores, para editarlo y hacer el tuyo.")
        exportar.clicked.connect(self._exportar_plantilla)
        fila.addWidget(abrir)
        fila.addWidget(exportar)
        fila.addStretch(1)
        self.b_abrir_temas, self.b_exportar_tema = abrir, exportar
        return fila

    def _tema_cambiado(self, *_):
        clave = self.controles["general/tema"].currentData()
        self._mostrar_aviso_tema(clave)
        self.tema_elegido.emit(clave)

    def _mostrar_aviso_tema(self, clave, extra=""):
        """Texto bajo el combo: lo que no cierra del tema elegido (contraste, archivos ignorados) y `extra`."""
        tema, avisos = temas.resolver(clave)
        partes = [extra] if extra else ["Se aplica al instante, sin reiniciar."]
        if iconos_tema.necesita_reiniciar(tema["colores"]):
            partes.append("⚠ Los íconos de las barras se adaptan a este tema al reiniciar OmniCAD.")
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

    def _cambio(self, *_):
        self.b_aplicar.setEnabled(True)

    # ------------------------------------------------------------ gráficos (al instante)
    def _poner(self, clave, valor):
        c = self.controles[clave]
        if isinstance(c, QComboBox):
            c.setCurrentIndex(max(c.findData(valor), 0))
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
        super().reject()

    def valores(self):
        salida = {}
        for clave, c in self.controles.items():
            if isinstance(c, QComboBox):
                salida[clave] = c.currentData()
            elif isinstance(c, QCheckBox):
                salida[clave] = c.isChecked()
            else:
                salida[clave] = c.value()
        return salida

    def _cargar(self):
        for clave, c in self.controles.items():
            valor = self.prefs[clave]
            if isinstance(c, QComboBox):
                c.setCurrentIndex(max(c.findData(valor), 0))
            elif isinstance(c, QCheckBox):
                c.setChecked(bool(valor))
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
