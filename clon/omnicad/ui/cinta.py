# -*- coding: utf-8 -*-
"""
Cinta de comandos al estilo de Fusion 360: selector de espacio de trabajo ("DISEÑO ▾"), pestañas
(SÓLIDO, SUPERFICIE, MALLA, CHAPA, PLÁSTICO, ADMINISTRAR, UTILIDADES) y, en cada pestaña, grupos
con botones grandes y un título desplegable ("CREAR ▾", "MODIFICAR ▾", …).

La estructura de los menús reproduce la que se ve en las capturas de Fusion que pasó el usuario; los
íconos fijos de cada grupo son los del video de Fusion 2026 (p. ej. SÓLIDO › CREAR: Extruir, Revolución,
Agujero, Patrón rectangular y Crear boceto).
Regla de honestidad: un comando que OmniCAD no implementa aparece GRISADO (igual que Fusion
muestra los que no están disponibles); nunca un botón activo que no hace nada. Los comandos
reales son QAction compartidas que crea la ventana y se buscan por clave.
"""
from PySide6.QtCore import QSize, Qt
from PySide6.QtGui import QAction
from PySide6.QtWidgets import (QFrame, QHBoxLayout, QLayout, QMenu, QSizePolicy, QStackedWidget, QToolButton,
                               QVBoxLayout, QWidget)

from .. import NOMBRE_APP, VERSION
from .cinta_boceto import GRUPOS_BOCETO
from .cinta_items import SEP, _i, _sub
from .iconos import icono

# ------------------------------------------------------------------ grupos compartidos entre pestañas
CONFIGURAR = ("CONFIGURAR", ["configurar"],
              [_i("Configurar", "configurar"), _i("Mostrar tabla de configuración", "mostrar_configuracion"),
               _i("Crear reglas de configuración")])
CONSTRUIR = ("CONSTRUIR", ["plano_desfase"], [
    _i("Sistema de coordenadas de usuario (SCU)", "scu"), SEP,
    _i("Plano de desfase", "plano_desfase"), _i("Plano en el ángulo", "plano_angulo"),
    _i("Plano tangente", "plano_tangente"), _i("Plano medio", "plano_medio"),
    _i("Plano perpendicular", "plano_perpendicular"), _i("Plano a través de dos aristas", "plano_dos_aristas"),
    _i("Plano a través de tres puntos", "plano_tres_puntos"), _i("Plano en ruta", "plano_ruta"), SEP,
    _i("Eje a través de cilindro/cono/toroide", "eje_cilindro"), _i("Eje perpendicular a la cara", "eje_perpendicular"),
    _i("Eje a través de dos planos", "eje_dos_planos"), _i("Eje a través de dos puntos", "eje_dos_puntos"),
    _i("Eje a través de arista", "eje_arista"), SEP,
    _i("Punto en vértice", "punto_vertice"), _i("Punto a través de dos aristas", "punto_dos_aristas"),
    _i("Punto a través de tres planos", "punto_tres_planos"),
    _i("Punto en el centro de círculo/esfera/toroide", "punto_centro"), _i("Punto en arista y plano", "punto_arista_plano"),
    _i("Punto a lo largo de la ruta", "punto_ruta")])
INSPECCIONAR = ("INSPECCIONAR", ["medir", "seccion"], [
    _i("Medir", "medir"), _i("Interferencia", "interferencia"), _i("Revisar geometría", "revisar_geometria"),
    _i("Reparar cuerpo", "reparar_cuerpo"), SEP,
    _i("Análisis de curvatura en peine", "curvatura_peine"), _i("Análisis cebra", "cebra"),
    _i("Análisis de mapas de entorno", "mapa_entorno"), _i("Análisis de ángulo de desmoldeo", "angulo_desmoldeo"),
    _i("Análisis del mapa de curvatura", "mapa_curvatura"), _i("Análisis de la isocurva", "isocurva"),
    _i("Análisis de accesibilidad", "accesibilidad"), _i("Análisis de radio mínimo", "radio_minimo"),
    _i("Análisis de sección", "seccion"), _i("Centro de masa", "centro_masa"), SEP,
    _i("Mostrar colores de componente", "colores_componente"),
    _i("Mostrar grupos de caras de malla", atajo="Mayúsculas+F")])
INSERTAR = ("INSERTAR", ["insertar_diseno", "lienzo", "fijacion"], [
    _i("Calcomanía", "calcomania"), _i("Lienzo", "lienzo"), _i("Insertar SVG", "insertar_svg"), _i("Vectorizar imagen", "vectorizar_imagen"),
    _i("Insertar archivos DXF", "insertar_dxf"),
    _i("Insertar malla", "insertar_malla"),
    _i("Insertar STEP…", "importar_step"), SEP, _i("Insertar fijación", "fijacion"),
    _i("Insertar componente", "insertar_diseno"), _i("Insertar derivación")])
ENSAMBLAR = ("ENSAMBLAR", ["union"], [
    _i("Nuevo componente", "nuevo_componente"), _i("Unión", "union"), _i("Unión como está", "union_construida"),
    _i("Origen de la unión", "origen_union"), _i("Grupo rígido", "grupo_rigido"), SEP,
    _i("Accionar uniones", "accionar_uniones"), _i("Vínculo de movimiento", "vinculo_movimiento"),
    _i("Fijar / liberar componente", "fijar_componente"), SEP,
    _i("Habilitar todos los conjuntos de contacto"), _i("Estudio de movimiento", "estudio_movimiento"), SEP,
    _i("Insertar componente…", "insertar_diseno")])
SELECCIONAR = ("SELECCIONAR", ["seleccionar"], [
    _i("Seleccionar", "seleccionar"), _i("Selección en ventana", "sel_ventana"),
    _i("Selección de forma libre", "sel_libre"), _i("Selección de pintura", "sel_pintura"), SEP,
    _sub("Herramientas de selección", [_i("Seleccionar todo", "seleccionar_todo"),
                                       _i("Invertir selección", "invertir_seleccion"),
                                       _i("Seleccionar por nombre", "seleccion_nombre"),
                                       _i("Seleccionar por tamaño", "seleccion_tamano")]),
    _sub("Prioridad de selección", [_i("Prioridad de cuerpo", "prioridad_cuerpo"), _i("Prioridad de cara", "prioridad_cara"),
                                    _i("Prioridad de arista", "prioridad_arista"),
                                    _i("Prioridad de componente", "prioridad_componente")]),
    _sub("Filtros de selección", [_i("Caras", "filtro_caras"), _i("Aristas", "filtro_aristas"),
                                  _i("Vértices", "filtro_vertices"), _i("Cuerpos", "filtro_cuerpos"),
                                  _i("Perfiles y curvas de boceto", "filtro_bocetos"),
                                  _i("Planos, ejes y puntos", "filtro_construccion")])])
COMPARTIDOS = [CONFIGURAR, CONSTRUIR, INSPECCIONAR, INSERTAR, ENSAMBLAR, SELECCIONAR]

# ------------------------------------------------------------------ pestañas
SOLIDO = [
    ("CREAR", ["extruir", "revolucion", "agujero", "patron_rectangular_3d", "boceto"], [
        _i("Crear boceto", "boceto"), _i("Crear forma"), _i("Derivar"), SEP,
        _i("Extruir", "extruir"), _i("Revolución", "revolucion"), _i("Barrido", "barrido"),
        _i("Solevación", "solevacion"), _i("Nervio", "nervio"), _i("Red", "red"), _i("Repujado", "repujado"), SEP,
        _i("Agujero", "agujero"), _i("Rosca", "rosca"), SEP,
        _i("Prisma rectangular", "caja"), _i("Cilindro", "cilindro"), _i("Esfera", "esfera"), _i("Toroide", "toroide"),
        _i("Bobina", "bobina"), _i("Tubería", "tuberia"), _i("Engranaje", "engranaje"), _i("Eje", "eje_escalonado"),
        SEP,
        _sub("Patrón", [_i("Patrón rectangular", "patron_rectangular_3d"), _i("Patrón circular", "patron_circular_3d"),
                        _i("Patrón en trayectoria", "patron_ruta")]),
        _i("Simetría", "simetria_3d"), SEP,
        _i("Engrosar", "engrosar"), _i("Llenado de contorno", "relleno_contorno"),
        _i("Sólido envolvente", "cuerpo_envolvente"), SEP,
        _i("Crear operación base", "operacion_base"), _sub("Crear placa de circuito impreso", []),
        _i("Origen de la unión", "origen_union")]),
    ("MODIFICAR", ["empalme_3d", "vaciado", "combinar", "dividir_cuerpo", "mover_copiar"], [
        _i("Pulsar/Tirar", "pulsar_tirar"), _i("Empalme", "empalme_3d"), _i("Chaflán", "chaflan_3d"), SEP,
        _i("Vaciado", "vaciado"), _i("Desmoldeo", "desmoldeo"), _i("Escala", "escala_3d"), _i("Combinar", "combinar"),
        _i("Cara de desfase", "desfase_cara"), _i("Reemplazar cara", "reemplazar_cara"), _i("Dividir cara", "dividir_cara"),
        _i("Dividir cuerpo", "dividir_cuerpo"), _i("División de silueta", "division_silueta"), SEP,
        _i("Mover/copiar", "mover_copiar"), _i("Alinear", "alinear"), _i("Suprimir", "suprimir"), _i("Quitar", "quitar"),
        SEP, _sub("Simplificar", []), SEP,
        _i("Material físico", "material_fisico"), _i("Aspecto", "aspecto"), _i("Administrar materiales"), SEP,
        _i("Cambiar parámetros", "parametros"), _i("Calcular todo", "calcular"), SEP,
        _i("Lista de materiales", "lista_materiales")]),
] + COMPARTIDOS


def _crear_y_modificar(crear, modificar):
    """Pestañas de otros entornos: el boceto es común a todos; el resto no está implementado."""
    return [("CREAR", ["boceto"] + [(t, i) for t, i in crear[:2]], [_i("Crear boceto", "boceto"), SEP] +
             [_i(t, ico=i) for t, i in crear]),
            ("MODIFICAR", [(modificar[0], "combinar")], [_i(t) for t in modificar])] + COMPARTIDOS


SUPERFICIE = [
    ("CREAR", ["boceto", "sup_extruir", "sup_revolucion", "parche", "sup_desfase"], [
        _i("Crear boceto", "boceto"), SEP,
        _i("Extruir", "sup_extruir"), _i("Revolución", "sup_revolucion"), _i("Barrido", "sup_barrido"),
        _i("Solevación", "sup_solevacion"), _i("Parche", "parche"), _i("Reglada", "reglada"),
        _i("Desfase", "sup_desfase"), SEP, _i("Engrosar", "engrosar")]),
    ("MODIFICAR", ["recortar_sup", "extender_sup", "coser", "engrosar"], [
        _i("Pulsar/Tirar", "pulsar_tirar"), _i("Empalme", "sup_empalme"), SEP,
        _i("Recortar", "recortar_sup"), _i("Destrimar", "destrimar"), _i("Extender", "extender_sup"),
        _i("Coser", "coser"), _i("Descoser", "descoser"), _i("Invertir normal", "invertir_normal"),
        _i("Engrosar", "engrosar"), SEP,
        _i("Cara de desfase", "desfase_cara"), _i("Reemplazar cara", "reemplazar_cara"),
        _i("Dividir cara", "dividir_cara"), _i("Dividir cuerpo", "dividir_cuerpo"), SEP,
        _i("Mover/copiar", "mover_copiar"), _i("Alinear", "alinear"), _i("Suprimir", "suprimir"), SEP,
        _i("Aspecto", "aspecto"), _i("Cambiar parámetros", "parametros"), _i("Calcular todo", "calcular")]),
] + COMPARTIDOS
CHAPA = [
    ("CREAR", ["boceto", "pestana", "pestana_contorno", "dobladillo"], [
        _i("Crear boceto", "boceto"), SEP, _i("Pestaña", "pestana"), _i("Pestaña de contorno", "pestana_contorno"),
        _i("Pestaña solevada"), _i("Dobladillo", "dobladillo"), SEP, _i("Convertir a chapa", "convertir_chapa")]),
    ("MODIFICAR", ["plegar", "desplegar", "patron_plano"], [
        _i("Plegar", "plegar"), _i("Desplegar", "desplegar"), _i("Volver a plegar caras", "replegar"),
        _i("Desgarro", "desgarro"), _i("Unir plegando", "unir_plegando"), _i("Cierre de esquina"), SEP,
        _i("Patrón plano", "patron_plano"), _i("Activar patrón plano", "activar_patron_plano"),
        _i("Exportar patrón plano a DXF", "exportar_dxf_chapa"), SEP,
        _i("Reglas de chapa", "reglas_chapa")]),
] + COMPARTIDOS
PLASTICO = [
    ("CREAR", ["boceto", "extruir", "nervio", "saliente", "labio"], [
        _i("Crear boceto", "boceto"), SEP, _i("Extruir", "extruir"), _i("Revolución", "revolucion"),
        _i("Nervio", "nervio"), _i("Red", "red"), _i("Saliente", "saliente"), _i("Labio y ranura", "labio"),
        _i("Encaje a presión"), _i("Apoyo")]),
    ("MODIFICAR", ["vaciado", "desmoldeo", "empalme_3d"], [
        _i("Vaciado", "vaciado"), _i("Desmoldeo", "desmoldeo"), _i("Empalme", "empalme_3d"),
        _i("Chaflán", "chaflan_3d"), SEP, _i("Reglas de plástico")]),
] + COMPARTIDOS
MALLA = [
    ("CREAR", ["insertar_malla", "malla_teselar"], [
        _i("Insertar malla", "insertar_malla"), _i("Malla de cuerpo B-Rep", "malla_teselar"),
        _i("Crear boceto de sección de malla")]),
    ("PREPARAR", ["reparar_malla", "grupos_caras"], [
        _i("Reparar", "reparar_malla"), _i("Generar grupos de caras", "grupos_caras"),
        _i("Combinar grupos de caras"), _i("Crear grupo de caras")]),
    ("MODIFICAR", ["reducir_malla", "remallar", "cortar_plano", "combinar_mallas", "convertir_malla"], [
        _i("Edición directa"), _i("Remallar", "remallar"), _i("Reducir", "reducir_malla"),
        _i("Corte de plano", "cortar_plano"), _i("Vaciado", "vaciado_malla"), _i("Combinar", "combinar_mallas"),
        _i("Suavizar", "suavizar_malla"), _i("Invertir normal", "invertir_normal_malla"), _i("Borrar y rellenar"),
        _i("Alinear"), _i("Extruir textura"), _i("Separar", "separar_malla"), _i("Escalar malla", "escalar_malla"),
        SEP, _i("Convertir malla", "convertir_malla")]),
] + COMPARTIDOS + [
    ("EXPORTAR", ["exportar_malla"], [_i("Exportar como malla (STL, OBJ, 3MF, PLY)…", "exportar_malla"),
                                      _i("Exportar STL…", "exportar_stl"), _i("Exportar OBJ…", "exportar_obj")])]
ADMINISTRAR = [("LISTA DE MATERIALES", ["lista_materiales"], [_i("Lista de materiales", "lista_materiales")])]
UTILIDADES = [
    ("CREAR", ["impresion3d"], [_i("Impresión en 3D…", "impresion3d")]),
    ("COMPLEMENTOS", ["secuencias"], [_i("Secuencias de comandos y complementos…", "secuencias")]),
    ("UTILIDAD", ["calcular"], [_i("Administrar materiales"), _i("Administrar biblioteca de roscas", "biblioteca_roscas"),
                                _i("Calcular todo", "calcular")]),
    INSPECCIONAR, SELECCIONAR]

# Pestaña contextual del entorno de boceto: sus grupos propios están en cinta_boceto.py.
BOCETO = GRUPOS_BOCETO + [CONFIGURAR, INSPECCIONAR, INSERTAR, ENSAMBLAR, SELECCIONAR,
                          ("TERMINAR BOCETO", ["sk_terminar"], [_i("", "sk_terminar")])]
CONTEXTUALES = [("BOCETO", BOCETO)]

LARGO_RENGLON = 10      # un nombre más largo que esto se parte en dos renglones bajo el ícono
ANCHO_SOLO_ICONO = 38   # botón de la cinta sin texto (ventana angosta)


def etiqueta_boton(texto):
    """Texto bajo el ícono de un botón de la cinta (docs/diseno/referencia_oscuro_moderno.webp): sin el atajo ni
    los puntos suspensivos, partido en el espacio más cercano al medio si es largo («Crear boceto» → «Crear» /
    «boceto»), y siempre en DOS renglones (el segundo puede ir vacío) para que todos los íconos de la fila queden a
    la misma altura."""
    texto = texto.split("\t")[0].replace("…", "").replace("...", "").strip()
    if len(texto) > LARGO_RENGLON and " " in texto:
        corte = min((i for i, c in enumerate(texto) if c == " "), key=lambda i: abs(i - len(texto) / 2))
        return texto[:corte] + "\n" + texto[corte + 1:]
    return texto + "\n "


PESTANAS = [("SÓLIDO", SOLIDO), ("SUPERFICIE", SUPERFICIE), ("MALLA", MALLA), ("CHAPA", CHAPA),
            ("PLÁSTICO", PLASTICO), ("ADMINISTRAR", ADMINISTRAR), ("UTILIDADES", UTILIDADES)]
ESPACIOS = ["DISEÑO", "DISEÑO GENERATIVO", "RENDERIZAR", "ANIMACIÓN", "SIMULACIÓN", "FABRICACIÓN", "DIBUJO", "ELECTRÓNICA"]


class Cinta(QWidget):
    """Barra de comandos con pestañas. `acciones`: dict clave → QAction de la ventana."""

    def __init__(self, acciones, parent=None):
        super().__init__(parent)
        self.setObjectName("cinta")
        self.setAttribute(Qt.WA_StyledBackground, True)
        self.acciones = acciones
        self.no_disponibles = []          # acciones grisadas (para pruebas y para la ayuda)
        lay = QHBoxLayout(self)
        lay.setContentsMargins(8, 2, 8, 0)
        lay.setSpacing(10)

        self.espacio = QToolButton(objectName="espacio_trabajo", text="DISEÑO  ▾")
        self.espacio.setFixedSize(108, 62)
        self.espacio.setPopupMode(QToolButton.InstantPopup)
        menu = QMenu(self.espacio)
        self.acciones_espacio = {}
        for nombre in ESPACIOS:
            a = menu.addAction(nombre)
            self.acciones_espacio[nombre] = a
            if nombre == "DISEÑO":
                a.setCheckable(True)
                a.setChecked(True)
            else:
                a.setEnabled(False)     # la ventana habilita los espacios que existen (DIBUJO, RENDERIZAR…)
                a.setToolTip(f"<b>{nombre}</b><br>No disponible en {NOMBRE_APP} {VERSION}.")
        menu.setToolTipsVisible(True)
        self.espacio.setMenu(menu)
        lay.addWidget(self.espacio, 0, Qt.AlignVCenter)

        derecha = QVBoxLayout()
        derecha.setSpacing(0)
        fila = QHBoxLayout()
        fila.setSpacing(6)
        self.pila = QStackedWidget()
        # Ancho «Ignored»: la ventana puede ser más angosta que la pestaña; ajustar_textos la compacta.
        self.pila.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Preferred)
        self.pestanas = []
        for i, (nombre, grupos) in enumerate(PESTANAS):
            b = QToolButton(objectName="pestana", text=nombre, checkable=True, autoExclusive=True)
            b.clicked.connect(lambda _=False, i=i: self.pila.setCurrentIndex(i))
            fila.addWidget(b)
            self.pestanas.append(b)
            self.pila.addWidget(self._fila_grupos(grupos))
        self.pestanas[0].setChecked(True)
        self.pila.currentChanged.connect(lambda _i: self.ajustar_textos())
        self.contextuales = {}
        for nombre, grupos in CONTEXTUALES:     # pestañas que aparecen solo en su entorno (BOCETO)
            b = QToolButton(objectName="pestana", text=nombre, checkable=True, autoExclusive=True)
            indice = self.pila.count()
            b.clicked.connect(lambda _=False, i=indice: self.pila.setCurrentIndex(i))
            b.hide()
            fila.addWidget(b)
            self.pila.addWidget(self._fila_grupos(grupos))
            self.contextuales[nombre] = b
        fila.addStretch(1)
        derecha.addLayout(fila)
        derecha.addWidget(self.pila)
        lay.addLayout(derecha, 1)

    # ------------------------------------------------------------ construcción
    def _accion(self, ref):
        """`ref` es una clave de acción real o (texto, ícono) para un comando no disponible."""
        if isinstance(ref, str):
            return self.acciones[ref]
        texto, ico = ref
        a = QAction(icono(ico) if ico else icono(""), texto, self)
        a.setEnabled(False)
        a.setToolTip(f"<b>{texto}</b><br>No disponible en {NOMBRE_APP} {VERSION}.")
        self.no_disponibles.append(a)
        return a

    def _fila_grupos(self, grupos):
        w = QWidget()
        h = QHBoxLayout(w)
        h.setContentsMargins(0, 0, 0, 0)
        h.setSpacing(4)
        for n, (titulo, rapidos, items) in enumerate(grupos):
            if n:
                sep = QFrame(objectName="separador_grupo")
                sep.setFixedWidth(1)
                h.addWidget(sep)
            h.addWidget(self._grupo(titulo, rapidos, items))
        h.addStretch(1)
        return w

    def _grupo(self, titulo, rapidos, items):
        w = QWidget()
        v = QVBoxLayout(w)
        v.setContentsMargins(2, 2, 2, 0)
        v.setSpacing(0)
        botones = QHBoxLayout()
        botones.setSpacing(2)
        for ref in rapidos:
            a = self._accion(ref)
            a.setIconText(etiqueta_boton(a.text()))     # solo lo usan los botones con texto; los menús usan text()
            b = QToolButton(objectName="boton_cinta")
            b.setDefaultAction(a)
            b.setIconSize(QSize(28, 28))
            b.setToolButtonStyle(Qt.ToolButtonTextUnderIcon)     # el ancho lo pone ajustar_textos, ya con la fuente del tema
            botones.addWidget(b)
        v.addLayout(botones)
        t = QToolButton(objectName="titulo_grupo", text=f"{titulo} ▾")
        t.setPopupMode(QToolButton.InstantPopup)
        t.setMenu(self._menu(items, t))
        v.addWidget(t, 0, Qt.AlignHCenter)
        return w

    def _menu(self, items, padre):
        m = QMenu(padre)
        m.setToolTipsVisible(True)
        for it in items:
            if it == SEP:
                m.addSeparator()
            elif it[0] == "sub":
                sub = m.addMenu(it[1])
                sub.setToolTipsVisible(True)
                for s in it[2]:
                    sub.addAction(self._item(s))
                # habilitado si tiene algún comando real (las acciones del boceto se activan después)
                sub.setEnabled(any(s[2] for s in it[2] if s != SEP))
            else:
                m.addAction(self._item(it))
        return m

    def _item(self, it):
        _, texto, clave, atajo, ico = it
        if clave:
            return self.acciones[clave]
        a = self._accion((texto, ico))
        if atajo:
            a.setText(f"{texto}\t{atajo}")    # el atajo se muestra como en Fusion pero NO se registra
        return a

    # ------------------------------------------------------------ texto bajo los íconos
    def resizeEvent(self, e):
        super().resizeEvent(e)
        self.ajustar_textos()

    def showEvent(self, e):
        super().showEvent(e)
        self.ajustar_textos()

    def ajustar_textos(self):
        """Si la pestaña visible no entra con el texto bajo los íconos (ventana angosta), sus botones quedan solo
        con el ícono; al volver a entrar, recuperan el texto. El ancho con texto se mide una vez por pestaña, con la
        cinta ya visible: antes la fuente del tema no está aplicada y la medida sale de más (1481 px en vez de 1110)."""
        pagina = self.pila.currentWidget()
        botones = pagina.findChildren(QToolButton, "boton_cinta") if pagina is not None and self.isVisible() else []
        if not botones:
            return
        ancho = pagina.property("ancho_con_texto")
        if ancho is None:
            for b in botones:
                self._estilo_boton(b, True)
            for lay in pagina.findChildren(QLayout) + [pagina.layout()]:
                lay.invalidate()            # sin esto, sizeHint devuelve el ancho viejo (sin texto) guardado en caché
            ancho = pagina.sizeHint().width()
            pagina.setProperty("ancho_con_texto", ancho)
        con_texto = self.pila.width() >= ancho
        for b in botones:
            self._estilo_boton(b, con_texto)

    @staticmethod
    def _estilo_boton(b, con_texto):
        # El ancho lo fija el renglón más largo: el sizeHint de QToolButton con texto bajo el ícono sale mucho más
        # ancho que el texto (medido: 77 px para «Extruir», que ocupa 33) y la cinta no entraba en 1586 px.
        if con_texto:
            renglones = b.text().split("\n")
            b.setFixedWidth(max(ANCHO_SOLO_ICONO + 10, max(b.fontMetrics().horizontalAdvance(r) for r in renglones) + 14))
            b.setToolButtonStyle(Qt.ToolButtonTextUnderIcon)
        else:
            b.setFixedWidth(ANCHO_SOLO_ICONO)
            b.setToolButtonStyle(Qt.ToolButtonIconOnly)

    def pestana_actual(self):
        todas = [n for n, _ in PESTANAS] + [n for n, _ in CONTEXTUALES]
        return todas[self.pila.currentIndex()]

    def mostrar_contextual(self, nombre):
        b = self.contextuales[nombre]
        b.show()
        b.click()

    def ocultar_contextual(self, nombre):
        b = self.contextuales[nombre]
        if b.isChecked():
            self.pestanas[0].click()
        b.hide()
