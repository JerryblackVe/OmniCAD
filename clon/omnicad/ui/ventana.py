# -*- coding: utf-8 -*-
"""
Ventana principal de OmniCAD.

Disposición copiada de las capturas de Fusion 360 que pasó el usuario:
  - columna izquierda: panel de datos ("Mis datos recientes");
  - arriba: barra de la aplicación (datos, archivo, guardar, deshacer/rehacer, pestaña del documento,
    ayuda y preferencias) y la cinta con pestañas y grupos desplegables;
  - centro: lienzo 3D oscuro con el navegador flotante, el ViewCube y la barra de navegación;
  - abajo: el timeline paramétrico.
Los bocetos se dibujan DENTRO de la vista 3D, como en Fusion: "Crear boceto" pide elegir un plano de
origen, un plano de construcción o una cara plana; la cámara mira ese plano, aparece la pestaña
BOCETO y la paleta de boceto, y "Terminar boceto" guarda el paso en el timeline. Al editar un boceto
se muestra el modelo como estaba en ese punto del timeline.
Esta capa no hace geometría: arma operaciones con los diálogos y se las pasa al Documento.
"""
import logging
import time
from pathlib import Path

import numpy as np

from PySide6.QtCore import QEvent, QObject, QSize, Qt, QTimer
from PySide6.QtGui import QAction, QActionGroup, QKeySequence
from PySide6.QtWidgets import (QApplication, QFileDialog, QHBoxLayout, QInputDialog, QLabel, QMainWindow, QMenu,
                               QMessageBox, QToolButton, QTreeWidget, QVBoxLayout, QWidget)

from .. import NOMBRE_APP, VERSION
from ..ejemplo import crear_documento_ejemplo
from ..io_archivos import abrir_externo, proyecto, puente_fusion
from ..io_archivos import exportar as ex
from ..nucleo import geometria as geo
from ..restricciones import Boceto
from ..timeline.documento import Documento, ErrorDocumento
from ..timeline.operaciones import OpBoceto, OpImportarSTEP, propiedades_cuerpo
from ..timeline.ops_chapa import es_patron_plano
from . import formato, temas
from .cinta import Cinta
from .comando import ContextoComando, PanelComando
from .comandos import CATALOGO, comando_para
from .dialogos import DialogoParametros, DialogoRejilla
from .iconos import icono
from .modo_boceto import ModoBoceto
from .navegador import ORIGEN, Navegador
from .panel_datos import PanelDatos
from .panel_timeline import PanelTimeline
from .preferencias import DETALLES, EFECTOS, PRESETS, DialogoPreferencias, Preferencias
from .superposiciones import AreaVisor, BarraNavegacion
from .visor3d import ENTORNOS, ESTILOS, Visor3D

log = logging.getLogger(__name__)
FILTRO_PROYECTO = "Proyectos OmniCAD (*.omnicad *.fclone)"     # .fclone: proyectos del nombre anterior
# Archivo › Abrir: además del proyecto, los formatos que Fusion abre con «Abrir desde mi equipo».
FILTRO_ABRIR = ";;".join([
    "Todos los archivos que se pueden abrir (*.omnicad *.fclone *.f3d *.f3z *.step *.stp *.iges *.igs *.stl *.obj "
    "*.3mf *.ply *.dxf *.brep *.brp)", FILTRO_PROYECTO, "Fusion 360 (*.f3d *.f3z)", "STEP (*.step *.stp)",
    "IGES (*.iges *.igs)", "Mallas (*.stl *.obj *.3mf *.ply)", "DXF (*.dxf)", "BREP de OpenCascade (*.brep *.brp)"])
VISIBILIDAD_INICIAL = {"todo": True, "origen": False, "planos": True, "cuerpos": True, "bocetos": True}
CLAVES_VISIBILIDAD = ("planos_origen", "ejes_origen", "punto_origen", "planos_usuario", "bocetos")
NOMBRES_TECLAS = (("Ctrl", "Control"), ("Shift", "Mayúsculas"), ("Del", "Suprimir"))


# Lo que se puede elegir con un clic sin comando abierto (Fusion: caras, aristas, vértices, perfiles…).
FILTRO_SELECCION = {"vertice", "arista", "cara", "perfil", "curva_boceto", "plano", "eje", "punto"}


def texto_atajo(secuencia):
    """'Ctrl+Shift+S' → 'Control+Mayúsculas+S', como lo escribe Fusion en sus menús."""
    texto = QKeySequence(secuencia).toString(QKeySequence.PortableText)
    for qt, es in NOMBRES_TECLAS:
        texto = texto.replace(qt, es)
    return texto


def dentro_del_poligono(puntos, poligono):
    """Qué puntos (N×2) caen dentro del polígono (M×2), con la regla par-impar (rayo hacia +x). Reemplaza a
    `matplotlib.path.Path.contains_points`: matplotlib no es una dependencia de OmniCAD (llegaba por vtk) y la app
    instalada no lo trae."""
    p = np.asarray(puntos, float).reshape(-1, 2)
    q = np.asarray(poligono, float).reshape(-1, 2)
    x, y = p[:, :1], p[:, 1:]
    x1, y1 = q[:, 0], q[:, 1]
    x2, y2 = np.roll(x1, -1), np.roll(y1, -1)
    cruza = (y1 > y) != (y2 > y)                    # el lado atraviesa la horizontal del punto
    with np.errstate(divide="ignore", invalid="ignore"):
        x_corte = x1 + (y - y1) * (x2 - x1) / (y2 - y1)
    return (cruza & (x < x_corte)).sum(axis=1) % 2 == 1


class _FiltroInfoHerramientas(QObject):
    """
    Preferencias → 'Mostrar información de herramientas' apagada: se tragan los tooltips.
    Se instala SOLO en botones y menús, y solo mientras la opción está apagada: un filtro Python
    sobre toda la aplicación interceptaba también los eventos del QOpenGLWidget y su
    initializeGL fallaba (glGetString → GL_INVALID_OPERATION, visto en la prueba de humo).
    """

    def eventFilter(self, _obj, evento):
        return evento.type() == QEvent.ToolTip


PIE_AYUDA = "<br><br><span style='color:#9a9a9a'>Pulse Ctrl+/ para obtener más ayuda.</span>"


class _FiltroAyuda(QObject):
    """Ctrl+/ sobre un comando de un menú abierto muestra su ayuda (los menús abiertos se quedan con el teclado,
    así que el atajo de la ventana no llega)."""

    def __init__(self, ventana):
        super().__init__(ventana)
        self.ventana = ventana

    def eventFilter(self, obj, evento):
        if (evento.type() == QEvent.KeyPress and evento.key() in (Qt.Key_Slash, Qt.Key_division)
                and evento.modifiers() & Qt.ControlModifier and isinstance(obj, QMenu) and obj.activeAction()):
            self.ventana.ayuda_comando(obj.activeAction())
            return True
        return False


class VentanaPrincipal(QMainWindow):
    def __init__(self, doc=None, prefs=None):
        super().__init__()
        self.resize(1600, 950)
        self._filtro_info = _FiltroInfoHerramientas(self)
        self.prefs = prefs or Preferencias()
        self._tema_aplicado = None          # tokens del tema que ya están en la aplicación
        self._avisos_tema = self.aplicar_tema()     # antes de crear los widgets: nacen con el estilo del tema
        self.doc = None
        self.ocultos = set()
        self.patron_activo = None           # id del patrón plano en pantalla (Activar patrón plano), o None
        self.vis = dict(VISIBILIDAD_INICIAL)
        self._camara_aplicada = None
        self._preset_aplicado = None
        self._eleccion = None               # "boceto" | "plano": qué se está eligiendo en la vista
        self.prefs_colores_componente = False   # INSPECCIONAR › Mostrar colores de componente (Mayús+N)
        self.panel = None                   # diálogo de comando abierto (PanelComando)
        self.caja = None                    # caja de herramientas (tecla S), se crea al primer uso
        self._estado_previa = None          # vista previa del comando abierto
        self._indice_boceto = None          # paso del boceto que se edita (vista "retrocedida")
        self.acciones = {}
        self._crear_acciones()
        self.modo_boceto = ModoBoceto(self)
        self.acciones.update(self.modo_boceto.acciones)
        self.modo_boceto.terminado.connect(self._boceto_terminado)

        self.visor = Visor3D()
        self.area = AreaVisor(self.visor)
        self.navegador = Navegador()
        self.area.anclar_arriba_izq(self.navegador)
        self.barra_nav = BarraNavegacion(self.visor, self)
        self.area.set_barra(self.barra_nav)
        self.navegador.ojo.connect(self._ojo)
        self.navegador.seleccionado.connect(self._propiedades)
        self.navegador.editar.connect(self.editar_operacion)
        self.navegador.vista_nueva.connect(self._vista_nueva)
        self.navegador.vista_ir.connect(self._vista_ir)
        self.navegador.vista_renombrar.connect(self._vista_renombrar)
        self.navegador.vista_borrar.connect(self._vista_borrar)
        self.navegador.accion.connect(self._accion_navegador)
        self.navegador.renombrado.connect(self._renombrar_desde_navegador)
        self.visor.plano_elegido.connect(self._plano_elegido)
        self.visor.eleccion_cancelada.connect(self._cancelar_eleccion)
        self.visor.eleccion_cancelada.connect(lambda: setattr(self, "_herramienta_pendiente", None))
        self.visor.entidad_elegida.connect(self._clic_en_vista)
        self.visor.clic_vacio.connect(lambda: self._seleccionar([]) if self.panel is None else None)
        self.visor.menu_contextual.connect(self._menu_vista)
        self.visor.gesto_radial.connect(self._gesto_radial)
        self.visor.seleccion_otra.connect(self._seleccion_otra)
        self._menu_radial = None
        self._herramienta_pendiente = None  # herramienta de boceto elegida en el menú radial antes del plano
        self.visor.seleccion_region.connect(self._seleccion_region)
        self.visor.entidad_pintada.connect(self._entidad_pintada)
        self.seleccion = []                 # lo elegido en la vista sin comando abierto (preselección)
        self._ultimo_comando = None         # para «Repetir» del menú contextual
        self.visor.set_filtro(FILTRO_SELECCION)
        for grupo in ("caras", "aristas", "vertices", "cuerpos", "bocetos", "construccion"):
            self.acciones[f"filtro_{grupo}"].setChecked(True)

        self.timeline = PanelTimeline()
        self.timeline.editar.connect(self.editar_operacion)
        self.timeline.renombrar.connect(self._renombrar)
        self.timeline.suprimir.connect(lambda i, v: self._intentar(lambda: self.doc.suprimir(i, v)))
        self.timeline.eliminar.connect(lambda i: self._intentar(lambda: self.doc.eliminar(i)))
        self.timeline.mover.connect(lambda i, n: self._intentar(lambda: self.doc.mover(i, n)))
        self.timeline.marcador.connect(lambda n: self._intentar(lambda: self.doc.mover_marcador(n)))
        self.timeline.buscar_navegador.connect(self.buscar_en_navegador)
        self.timeline.animar_union.connect(self.animar_union)
        self._crear_menu_unidades()

        self.panel_datos = PanelDatos(self.prefs)
        self.panel_datos.abrir.connect(self._abrir_reciente)
        self.panel_datos.cerrar.connect(lambda: self.acciones["panel_datos"].setChecked(False))
        self.cinta = Cinta(self.acciones)
        self._espacios = {}                 # espacio de trabajo → su ventana (DIBUJO, RENDERIZAR, ANIMACIÓN)
        for nombre, clave in (("DIBUJO", "dibujo"), ("RENDERIZAR", "render"), ("ANIMACIÓN", "animacion")):
            a = self.cinta.acciones_espacio[nombre]
            if self._clase_espacio(clave) is not None:
                a.setEnabled(True)
                a.setToolTip("")
                a.triggered.connect(lambda _=False, c=clave: self.abrir_espacio(c))

        derecha = QVBoxLayout()
        derecha.setContentsMargins(0, 0, 0, 0)
        derecha.setSpacing(0)
        derecha.addWidget(self._crear_barra_app())
        derecha.addWidget(self.cinta)
        derecha.addWidget(self.area, 1)
        derecha.addWidget(self.timeline)
        central = QWidget()
        h = QHBoxLayout(central)
        h.setContentsMargins(0, 0, 0, 0)
        h.setSpacing(0)
        h.addWidget(self.panel_datos)
        h.addLayout(derecha, 1)
        self.setCentralWidget(central)

        self._texto_estado = ""
        self._t_mensaje = QTimer(self, singleShot=True)
        self._t_mensaje.timeout.connect(lambda: self._mostrar_estado(self._info_sel or self._texto_estado))
        self._info_sel = ""                 # medidas de lo elegido ("1 Perfil | Área: …"), abajo a la derecha
        self._avisos_vistos = None          # avisos/errores del timeline ya anunciados con el aviso flotante
        self.temporizador = QTimer(self)
        self.temporizador.timeout.connect(self.autoguardar)
        self.puente = None                  # puente para agentes IA (MCP en vivo): ui/puente.py
        self._puente_sesion = False         # encendido con --puente solo para esta sesión
        self._pref_puente = None            # valor de la preferencia la última vez que se aplicó
        self._vista_inicial()
        self.aplicar_preferencias()
        from .comentarios import PanelComentarios
        self.comentarios = PanelComentarios()
        self.area.anclar_abajo_izq(self.comentarios)
        self._filtro_ayuda = _FiltroAyuda(self)
        for menu in self.findChildren(QMenu):
            menu.installEventFilter(self._filtro_ayuda)
        self.set_documento(doc or Documento())
        if self._avisos_tema:
            self.mensaje(self._avisos_tema[0], 10000)

    # ------------------------------------------------------------ acciones (comandos)
    def _accion(self, clave, texto, funcion, atajo=None, ayuda=None, ico=None, marcable=False):
        a = QAction(texto, self)
        if ico:
            a.setIcon(icono(ico))
        if atajo:
            a.setShortcut(QKeySequence(atajo))
            a.setText(f"{texto}\t{texto_atajo(atajo)}")
        a.setToolTip(f"<b>{texto}</b>" + (f"<br>{ayuda}" if ayuda else "") +
                     (f"<br><span style='color:#bbbbbb'>{texto_atajo(atajo)}</span>" if atajo else "") +
                     (PIE_AYUDA if ayuda else ""))
        a.setCheckable(marcable)
        a.triggered.connect(funcion)
        self.addAction(a)                   # así el atajo funciona aunque el menú esté cerrado
        self.acciones[clave] = a
        return a

    def _crear_acciones(self):
        A = self._accion
        A("nuevo", "Nuevo diseño", self.nuevo, "Ctrl+N")
        A("abrir", "Abrir…", self.abrir, "Ctrl+O", "Abrir un proyecto .omnicad")
        A("recuperados", "Abrir documentos recuperados", self.verificar_autoguardado_huerfano)
        A("guardar", "Guardar", self.guardar, "Ctrl+S", "Guardar el proyecto", "guardar")
        A("guardar_como", "Guardar como…", self.guardar_como, "Ctrl+Shift+S")
        A("exportar", "Exportar…", lambda: self.exportar(None), None, "Exportar los cuerpos a STL, OBJ o STEP", "exportar")
        A("exportar_stl", "Exportar STL…", lambda: self.exportar("stl"), None, "Malla triangulada para impresión 3D", "exportar")
        A("exportar_obj", "Exportar OBJ…", lambda: self.exportar("obj"), None, "Malla triangulada", "exportar")
        A("impresion3d", "Impresión en 3D…", lambda: self.exportar("stl"), None,
          "Exporta los cuerpos a STL para abrirlos en el laminador", "impresion3d")
        A("captura", "Capturar imagen…", self.capturar_imagen, None, "Guardar la vista actual como PNG", "captura")
        A("ejemplo", "Cargar modelo de ejemplo", self.cargar_ejemplo)
        A("salir", "Salir", self.close, "Ctrl+Q")
        A("deshacer", "Deshacer", self._deshacer, "Ctrl+Z", None, "deshacer")
        A("rehacer", "Rehacer", lambda: self._intentar(self.doc.rehacer), "Ctrl+Y", None, "rehacer")
        A("boceto", "Crear boceto", self.crear_boceto, "B", "Elegí un plano de origen, un plano de construcción o "
          "una cara plana y dibujá sobre él en la vista 3D. Los contornos cerrados se pueden extruir o revolucionar.",
          "boceto")
        for clave, clase in CATALOGO.items():
            if clave == "suprimir":
                funcion = self._tecla_suprimir
            elif getattr(clase, "EXTENSIONES", ()):
                funcion = lambda _=False, c=clase: self._insertar_archivo(c)  # noqa: E731
            else:
                funcion = lambda _=False, c=clase: self.ejecutar_comando(c())  # noqa: E731
            A(clave, clase.TITULO, funcion, getattr(clase, "ATAJO", None), getattr(clase, "AYUDA", None), clase.ICONO)
        # caja, cilindro, esfera y toroide: comandos con panel de `comandos/primitivas.py` (ya están en CATALOGO)
        A("parametros", "Cambiar parámetros", self.parametros, "Ctrl+P",
          "Parámetros de usuario con nombre, expresión y unidad. Todo el modelo se recalcula.", "parametros")
        A("calcular", "Calcular todo", self.calcular_todo, "Ctrl+B", "Vuelve a calcular todo el timeline.", "calcular")
        A("activar_patron_plano", "Activar patrón plano", self.alternar_patron_plano, None,
          "Muestra solo el patrón plano de la chapa elegida (o del último creado); otra vez vuelve al modelo plegado.",
          "patron_plano", True)
        A("colores_componente", "Mostrar colores de componente", self._colores_componente, "Shift+N",
          "Pinta cada cuerpo con un color distinto para distinguirlos.", "colores_componente", True)
        A("importar_step", "Insertar STEP…", self.importar_step, None, "Inserta un archivo STEP como un paso del timeline.",
          "importar")
        A("lista_materiales", "Lista de materiales", self.lista_materiales, None,
          "Componentes y cuerpos con cantidad, material y masa; se exporta a CSV.", "lista_materiales")
        A("configurar", "Tabla de configuración", self.configurar, None,
          "Variantes del diseño: cada fila cambia parámetros y suprime pasos.", "configuracion_tabla")
        A("mostrar_configuracion", "Mostrar tabla de configuración", self.configurar, None,
          "Abre la tabla de configuraciones del diseño.", "configuracion_tabla")
        A("secuencias", "Secuencias de comandos y complementos…", self.secuencias, "Shift+S",
          "Ejecuta scripts de Python sobre el diseño.", "secuencias")
        A("biblioteca_roscas", "Administrar biblioteca de roscas", self.biblioteca_roscas, None,
          "Consulta las roscas ISO y unificadas disponibles.", "rosca")
        A("operacion_base", "Crear operación base", self.operacion_base, None,
          "Congela cuerpos elegidos (sin historial), como la operación base de Fusion.", "operacion_base")
        A("nuevo_dibujo", "Nuevo dibujo desde el diseño", lambda: self.abrir_espacio("dibujo"), None,
          "Abre el espacio DIBUJO: vistas 2D, cotas y exportación a PDF/DXF.", "dibujo")
        A("insertar_diseno", "Insertar componente…", self.insertar_diseno, None,
          "Inserta otro diseño de OmniCAD (.omnicad) como componente.", "insertar_componente")
        A("estudio_movimiento", "Estudio de movimiento", self._estudio_movimiento, None,
          "Anima una unión en todo su recorrido.", "estudio_movimiento")
        A("insertar_malla", "Insertar malla…", self.insertar_malla, None,
          "Inserta un archivo STL, OBJ, 3MF o PLY como cuerpo de malla.", "insertar_malla")
        A("exportar_malla", "Exportar como malla…", lambda: self.exportar(("3mf", "stl", "obj", "ply")), None,
          "Guarda los cuerpos como malla: STL, OBJ, 3MF o PLY.", "exportar_malla")
        A("seleccionar", "Seleccionar", self.accion_seleccionar, None,
          "Vuelve a seleccionar: sale de la herramienta de boceto activa (línea, círculo…) y de los modos de "
          "navegación (órbita, encuadre, zoom) y de selección por región.", "seleccionar")
        A("caja_herramientas", "Caja de herramientas", self.abrir_caja_herramientas, "S",
          "Buscá y usá cualquier comando, y fijá los que más usás (en un boceto, con su propia lista).", "chinche")
        A("ayuda_comando", "Ayuda del comando", lambda: self.ayuda_comando(), "Ctrl+/",
          "Con el ratón sobre un comando de la cinta o de un menú, muestra su ayuda.")
        A("renombrar", "Renombrar", lambda: self.navegador.renombrar_en_linea(), "F2",
          "Renombra en el navegador el elemento elegido.")
        A("ajustar", "Ajustar", lambda: self.visor.encuadrar(), "F6", "Encuadra todo el modelo en la vista.", "ajustar")
        for clave, texto in (("iso", "Vista inicial (isométrica)"), ("frente", "Frente"), ("arriba", "Superior"),
                             ("derecha", "Derecha")):
            A(f"vista_{clave}", texto, lambda _=False, c=clave: self.visor.vista(c))
        # SELECCIONAR (en Fusion 1, 2 y 3 son los modos de selección por región)
        A("sel_ventana", "Selección en ventana", lambda: self._modo_seleccion("sel_ventana"), "1",
          "Arrastrá un rectángulo: de izquierda a derecha elige lo que queda adentro; al revés, lo que toca.",
          "seleccion_ventana")
        A("sel_libre", "Selección de forma libre", lambda: self._modo_seleccion("sel_libre"), "2",
          "Dibujá un lazo alrededor de lo que querés elegir.", "seleccion_libre")
        A("sel_pintura", "Selección de pintura", lambda: self._modo_seleccion("sel_pintura"), "3",
          "Arrastrá sobre las caras o cuerpos para irlos sumando.", "seleccion_pintura")
        A("seleccionar_todo", "Seleccionar todo", self._seleccionar_todo, "Ctrl+A", "Elige todos los cuerpos visibles.")
        A("invertir_seleccion", "Invertir selección", self._invertir_seleccion, None, "Elige los cuerpos no elegidos.")
        A("seleccion_nombre", "Seleccionar por nombre…", self._seleccion_nombre, None, "Elige cuerpos por su nombre.")
        A("seleccion_tamano", "Seleccionar por tamaño…", self._seleccion_tamano, None,
          "Elige cuerpos cuya caja envolvente está entre dos tamaños.")
        for clave, texto in (("cuerpo", "Prioridad de cuerpo"), ("cara", "Prioridad de cara"),
                             ("arista", "Prioridad de arista"), ("componente", "Prioridad de componente")):
            A(f"prioridad_{clave}", texto, lambda _=False, c=clave: self._prioridad(c), None, None, None, True)
        for clave, texto in (("caras", "Caras"), ("aristas", "Aristas"), ("vertices", "Vértices"),
                             ("cuerpos", "Cuerpos"), ("bocetos", "Perfiles y curvas de boceto"),
                             ("construccion", "Planos, ejes y puntos")):
            A(f"filtro_{clave}", texto, lambda activo, c=clave: self._filtro_seleccion(c, activo), None, None, None,
              True)
        A("preferencias", "Preferencias…", self.preferencias, None, "Preferencias de OmniCAD", "engranaje")
        A("acerca", f"Acerca de {NOMBRE_APP}", self.acerca_de)
        A("panel_datos", "Panel de datos", self._mostrar_panel_datos, None,
          "Mostrar u ocultar el panel de datos (proyectos recientes)", "datos", True)
        for clave, texto in (("ver_navegador", "Navegador"), ("ver_viewcube", "ViewCube"),
                             ("ver_barra_nav", "Barra de navegación"), ("ver_timeline", "Timeline")):
            A(clave, texto, lambda activo, c=clave: self._mostrar_elemento(c, activo), None, None, None, True)

    def _boton(self, accion, ico_tam=18):
        b = QToolButton()
        b.setDefaultAction(accion)
        b.setIconSize(QSize(ico_tam, ico_tam))
        b.setToolButtonStyle(Qt.ToolButtonIconOnly)
        return b

    def _crear_barra_app(self):
        barra = QWidget(objectName="barra_app")
        barra.setAttribute(Qt.WA_StyledBackground, True)
        h = QHBoxLayout(barra)
        h.setContentsMargins(6, 4, 6, 0)
        h.setSpacing(2)
        h.addWidget(self._boton(self.acciones["panel_datos"]))

        m = QMenu(self)
        m.setToolTipsVisible(True)
        for clave in ("nuevo",):
            m.addAction(self.acciones[clave])
        a = m.addAction("Añadir a ensamblaje")
        a.setEnabled(False)
        for clave in ("abrir", "recuperados", None, "guardar", "guardar_como", "exportar", None, "nuevo_dibujo",
                      "impresion3d", "captura", None, "ejemplo"):
            m.addSeparator() if clave is None else m.addAction(self.acciones[clave])
        m.addSeparator()
        vista = m.addMenu("Vista")
        for clave in ("panel_datos", "ver_navegador", "ver_viewcube", "ver_barra_nav", "ver_timeline"):
            vista.addAction(self.acciones[clave])
        m.addSeparator()
        m.addAction(self.acciones["salir"])
        m.aboutToShow.connect(lambda: self.acciones["recuperados"].setEnabled(
            proyecto.autoguardado_pendiente(None) is not None))
        self.menu_archivo = m
        archivo = QToolButton()
        archivo.setIcon(icono("archivo"))
        archivo.setIconSize(QSize(18, 18))
        archivo.setText(" ▾")
        archivo.setToolButtonStyle(Qt.ToolButtonTextBesideIcon)
        archivo.setToolTip("<b>Archivo</b>")
        archivo.setPopupMode(QToolButton.InstantPopup)
        archivo.setMenu(m)
        h.addWidget(archivo)
        for clave in ("guardar", "deshacer", "rehacer"):
            h.addWidget(self._boton(self.acciones[clave]))
        h.addSpacing(10)
        self.pestana_doc = QLabel(objectName="pestana_doc", alignment=Qt.AlignCenter)
        self.pestana_doc.setMinimumWidth(200)
        h.addWidget(self.pestana_doc, 1)
        h.addSpacing(10)
        ayuda = QToolButton()
        ayuda.setIcon(icono("ayuda"))
        ayuda.setIconSize(QSize(18, 18))
        ayuda.setToolTip("<b>Ayuda</b>")
        ayuda.setPopupMode(QToolButton.InstantPopup)
        menu_ayuda = QMenu(self)
        menu_ayuda.addAction(self.acciones["acerca"])
        ayuda.setMenu(menu_ayuda)
        h.addWidget(ayuda)
        h.addWidget(self._boton(self.acciones["preferencias"]))
        return barra

    # ------------------------------------------------------------ paneles y preferencias
    def _vista_inicial(self):
        p, c = self.prefs, self.visor.config
        self.acciones["panel_datos"].setChecked(p["vista/panel_datos"])
        self.panel_datos.setVisible(p["vista/panel_datos"])
        for clave in ("ver_navegador", "ver_viewcube", "ver_barra_nav", "ver_timeline"):
            self.acciones[clave].setChecked(True)
        c.estilo_visual = p["vista/estilo_visual"] if p["vista/estilo_visual"] in ESTILOS else "sombreado_aristas"
        c.entorno = p["vista/entorno"] if p["vista/entorno"] in ENTORNOS else "tema"
        c.rejilla, c.rejilla_bloqueada, c.desfase_suelo = (p["vista/rejilla"], p["vista/rejilla_bloqueada"],
                                                           p["vista/desfase_suelo"])
        try:
            mayor, sub = p["vista/rejilla_fija"].split(",")
            c.rejilla_fija = (float(mayor), int(sub))
        except ValueError:
            c.rejilla_fija = None
        c.visibilidad = {k: p[f"vista/vis_{k}"] for k in CLAVES_VISIBILIDAD}
        self.barra_nav.set_estilo(c.estilo_visual)

    def aplicar_tema(self, clave=None):
        """Preferencias › General › Tema: activa `clave` (o el guardado) en la aplicación entera —QSS, paleta y fondo
        de la vista 3D— sin reiniciar. Devuelve los avisos (un archivo de tema inválido se ignora, no rompe nada)."""
        avisos = temas.activar(clave or self.prefs["general/tema"])
        for a in avisos:
            log.warning("tema: %s", a)
        if dict(temas.activo()) != self._tema_aplicado:
            self._tema_aplicado = dict(temas.activo())
            temas.aplicar_a_app(QApplication.instance())
            if hasattr(self, "area"):                      # ya hay ventana armada: repintar lo que pinta a mano
                for v in self.area.visores:
                    v.update()
                for arbol in self.findChildren(QTreeWidget):
                    arbol.viewport().update()
        return avisos

    def aplicar_preferencias(self):
        p, c = self.prefs, self.visor.config
        avisos = self.aplicar_tema()
        if avisos and self.isVisible():
            self.mensaje(avisos[0], 10000)
        self.temporizador.start(p["general/autoguardado_min"] * 60_000)
        c.esquema_raton, c.invertir_zoom = p["general/raton"], p["general/invertir_zoom"]
        c.aspecto, c.tipo_orbita = p["material/aspecto"], p["general/tipo_orbita"]
        if p["general/camara"] != self._camara_aplicada:     # solo si cambió: no pisa la cámara elegida a mano
            self._camara_aplicada = p["general/camara"]
            c.camara = self._camara_aplicada
        # Valor predefinido de gráficos: elegir uno fija todo junto; tocar una de sus claves pasa a "Personalizar".
        preset = p["graficos/preset"]
        if preset != self._preset_aplicado:
            if preset in PRESETS and self._preset_aplicado is not None:
                for clave, valor in PRESETS[preset].items():
                    p[clave] = valor
            self._preset_aplicado = preset
        elif preset in PRESETS and any(p[clave] != valor for clave, valor in PRESETS[preset].items()):
            p["graficos/preset"] = self._preset_aplicado = "personalizar"
        c.efectos = {k: p[f"vista/efecto_{k}"] for k in EFECTOS}
        c.dinamico, c.fps_minimo, c.limite_fps = p["graficos/dinamico"], p["graficos/fps_minimo"], p["graficos/limite_fps"]
        teselado, angular = DETALLES.get(p["graficos/detalle"], DETALLES["automatico"])
        if (teselado, angular) != (c.teselado, c.angular):
            c.teselado, c.angular = teselado, angular
            for v in self.area.visores:
                v.invalidar_teselado()
            if self.doc is not None:
                self._refrescar_visibilidad()
        self.area.viewcube.set_tamano(p["general/tamano_viewcube"])
        self.area.reubicar()
        self._info_herramientas(p["general/info_herramientas"])
        formato.configurar(p["unidades/precision"], p["unidades/precision_angular"], p["unidades/ocultar_ceros"])
        for v in self.area.visores:
            v.update()
        self._aplicar_puente()

    # ------------------------------------------------------------ puente para agentes IA (MCP en vivo)
    def encender_puente(self):
        """`OmniCAD.py --puente`: lo enciende en esta sesión aunque la preferencia esté apagada."""
        self._puente_sesion = True
        return self._aplicar_puente()

    def _aplicar_puente(self):
        """Prende o apaga el puente según la preferencia (o --puente), sin reiniciar. Si el usuario cambia la
        preferencia en el diálogo, su elección manda sobre --puente."""
        pref = self.prefs["general/puente_agentes"]
        if self._pref_puente is not None and pref != self._pref_puente:
            self._puente_sesion = False
        self._pref_puente = pref
        if pref or self._puente_sesion:
            if self.puente is None:
                from .puente import PuenteAgentes
                self.puente = PuenteAgentes(self)
            if not self.puente.activo and not self.puente.iniciar():
                self.mensaje("No se pudo encender el puente para agentes IA (puertos ocupados o carpeta sin permiso).", 8000)
            return self.puente.activo
        if self.puente is not None:
            self.puente.detener()
        return False

    # ------------------------------------------------------------ opciones de la barra de navegación
    def valor_vista(self, clave):
        c = self.visor.config
        if clave.startswith("efecto:"):
            return c.efectos.get(clave.split(":")[1], False)
        if clave == "visibilidad:todas":
            return all(c.visibilidad.values())
        if clave.startswith("visibilidad:"):
            return c.visibilidad.get(clave.split(":")[1], False)
        return {"estilo_visual": c.estilo_visual, "entorno": c.entorno, "preset": self.prefs["graficos/preset"],
                "camara": c.camara, "desfase_suelo": c.desfase_suelo, "rejilla": c.rejilla,
                "rejilla_bloqueada": c.rejilla_bloqueada, "forzar_rejilla": self.prefs["vista/forzar_rejilla"],
                "vistas_multiples": self.area.multiples, "tipo_orbita": c.tipo_orbita}.get(clave)

    def cambiar_vista(self, clave, valor):
        p, c = self.prefs, self.visor.config
        if clave == "estilo_visual":
            c.estilo_visual = p["vista/estilo_visual"] = valor
        elif clave == "entorno":
            c.entorno = p["vista/entorno"] = valor
        elif clave == "preset":
            p["graficos/preset"] = valor
            self.aplicar_preferencias()
        elif clave.startswith("efecto:"):
            p[f"vista/efecto_{clave.split(':')[1]}"] = bool(valor)
            self.aplicar_preferencias()
        elif clave.startswith("visibilidad:"):
            k = clave.split(":")[1]
            for clave_v in (CLAVES_VISIBILIDAD if k == "todas" else (k,)):
                c.visibilidad[clave_v] = p[f"vista/vis_{clave_v}"] = bool(valor)
        elif clave == "camara":
            c.camara = valor
        elif clave == "desfase_suelo":
            c.desfase_suelo = p["vista/desfase_suelo"] = bool(valor)
        elif clave == "rejilla":
            c.rejilla = p["vista/rejilla"] = bool(valor)
        elif clave == "rejilla_bloqueada":
            c.paso_bloqueado = self.visor.paso_rejilla() if valor else None
            c.rejilla_bloqueada = p["vista/rejilla_bloqueada"] = bool(valor)
        elif clave == "forzar_rejilla":
            p["vista/forzar_rejilla"] = bool(valor)
            if self.modo_boceto.activo:
                self.modo_boceto.set_forzar(bool(valor))
        elif clave == "vistas_multiples":
            if valor and self.modo_boceto.activo:
                self.mensaje("Las vistas múltiples no se usan mientras se edita un boceto.")
                return
            self.area.set_vistas_multiples(bool(valor), self._preparar_vista)
            self._refrescar_visibilidad()
        elif clave == "tipo_orbita":
            c.tipo_orbita = p["general/tipo_orbita"] = valor
        for v in self.area.visores:
            v.update()

    def _preparar_vista(self, visor, vista):
        visor.forzar_orto = True
        visor.vista(vista)

    def pantalla_completa(self):
        if self.isFullScreen():
            self.showMaximized()
        else:
            self.showFullScreen()

    def parametros_rejilla(self):
        c = self.visor.config
        dlg = DialogoRejilla(c.rejilla_fija, self)
        if dlg.exec():
            c.rejilla_fija = dlg.valor()
            self.prefs["vista/rejilla_fija"] = ",".join(map(str, c.rejilla_fija)) if c.rejilla_fija else ""
            for v in self.area.visores:
                v.update()

    def mirar_a(self):
        """Barra de navegación › Mirar a: en un boceto mira su plano; si no, la barra pide elegir."""
        if self.modo_boceto.activo:
            self.visor.mirar_a_plano(self.modo_boceto.plano)
            return True
        return False

    def _info_herramientas(self, mostrar):
        destinos = self.findChildren(QToolButton) + self.findChildren(QMenu) + [self.timeline.lista.viewport(),
                                                                               self.area.viewcube]
        for w in destinos:
            w.removeEventFilter(self._filtro_info)
            if not mostrar:
                w.installEventFilter(self._filtro_info)

    def preferencias(self, _marcado=False, pagina="general"):
        dlg = DialogoPreferencias(self.prefs, self, pagina)
        dlg.aplicado.connect(self.aplicar_preferencias)
        dlg.tema_elegido.connect(self.aplicar_tema)         # vista previa al instante, antes de Aplicar
        dlg.graficos_cambiados.connect(self.aplicar_preferencias)   # Gráficos: al instante
        dlg.rejected.connect(lambda: self.aplicar_tema())   # Cancelar: vuelve al tema guardado
        dlg.exec()

    def ayuda_comando(self, accion=None):
        """Ctrl+/ como en Fusion: la ayuda del comando que está bajo el ratón (botón de la cinta o fila de un
        menú), con su descripción, dónde está y su atajo."""
        if accion is None:
            from PySide6.QtGui import QCursor
            w = QApplication.widgetAt(QCursor.pos())
            while w is not None and accion is None:
                if isinstance(w, QMenu):
                    accion = w.activeAction()
                elif isinstance(w, QToolButton):
                    accion = w.defaultAction()
                w = w.parentWidget()
        if accion is None or not accion.text():
            QMessageBox.information(self, "Ayuda", "Pasá el ratón sobre un comando de la cinta o de un menú y pulsá "
                                    "Ctrl+/ para ver su ayuda.")
            return None
        nombre = accion.text().split("\t")[0]
        texto = (accion.toolTip() or f"<b>{nombre}</b>").replace(PIE_AYUDA, "")
        if not accion.isEnabled():
            texto += "<br><br><i>Ahora no está disponible (puede pedir algo elegido o estar fuera de este entorno).</i>"
        caja = QMessageBox(self)
        caja.setWindowTitle(f"Ayuda: {nombre}")
        caja.setTextFormat(Qt.RichText)
        caja.setText(texto)
        if not accion.icon().isNull():
            caja.setIconPixmap(accion.icon().pixmap(48, 48))
        caja.setStandardButtons(QMessageBox.Ok)
        caja.open()
        self._caja_ayuda = caja
        return caja

    def _crear_menu_unidades(self):
        """Menú de «Unidades: mm, g ▾» en la barra de abajo. El modelo trabaja en mm y g: las demás unidades se ven
        grisadas (no implementadas, como en la cinta). Lo que sí cambia es la precisión con que se muestran los
        valores, la misma preferencia que Preferencias › Visualización de unidad y valor."""
        m = QMenu(self)
        m.setToolTipsVisible(True)
        no_disp = f"No disponible en {NOMBRE_APP} {VERSION}: el modelo trabaja en milímetros y gramos."
        for titulo, unidades, nota in (
                ("Longitud", ["Milímetro (mm)", "Centímetro (cm)", "Metro (m)", "Pulgada (in)", "Pie (ft)"],
                 "<br>En cualquier campo se puede escribir otra unidad (2 in, 5 cm) y se pasa a mm."),
                ("Masa", ["Gramo (g)", "Kilogramo (kg)", "Libra (lb)"], "")):
            m.addSection(titulo)
            grupo = QActionGroup(m)
            for i, texto in enumerate(unidades):
                a = m.addAction(texto)
                a.setCheckable(True)
                a.setChecked(i == 0)
                a.setEnabled(i == 0)
                if i:
                    a.setToolTip(no_disp + nota)
                grupo.addAction(a)
        m.addSeparator()
        precision = m.addMenu("Precisión")
        grupo = QActionGroup(precision)
        for n in range(6):
            a = precision.addAction("0" if n == 0 else "0." + "123456"[:n])
            a.setCheckable(True)
            a.setData(n)
            a.triggered.connect(lambda _=False, n=n: self._pref_unidades("unidades/precision", n))
            grupo.addAction(a)
        ceros = m.addAction("Ocultar ceros finales")
        ceros.setCheckable(True)
        ceros.triggered.connect(lambda v: self._pref_unidades("unidades/ocultar_ceros", bool(v)))
        m.addSeparator()
        m.addAction("Preferencias de unidades…").triggered.connect(lambda: self.preferencias(pagina="valores"))

        def sincronizar():                  # Preferencias puede haberlas cambiado desde la última vez
            for a in grupo.actions():
                a.setChecked(a.data() == self.prefs["unidades/precision"])
            ceros.setChecked(bool(self.prefs["unidades/ocultar_ceros"]))
        m.aboutToShow.connect(sincronizar)
        self.menu_unidades = m
        self.timeline.unidades.setMenu(m)

    def abrir_caja_herramientas(self):
        """Tecla S: la caja de herramientas junto al ratón (atajos de boceto si hay un boceto abierto)."""
        from .caja_herramientas import CajaHerramientas
        if self.caja is None:
            self.caja = CajaHerramientas(self.acciones, self.prefs, self)
        pos = self.caja.pos_raton()
        if not self.rect().contains(pos):
            pos = self.rect().center()
        self.caja.abrir("boceto" if self.modo_boceto.activo else "diseno", pos)

    def _pref_unidades(self, clave, valor):
        self.prefs[clave] = valor
        self.aplicar_preferencias()

    def _mostrar_panel_datos(self, visible):
        self.panel_datos.setVisible(visible)
        self.prefs["vista/panel_datos"] = bool(visible)

    def _mostrar_elemento(self, clave, visible):
        {"ver_navegador": self.navegador, "ver_viewcube": self.area.viewcube, "ver_barra_nav": self.barra_nav,
         "ver_timeline": self.timeline}[clave].setVisible(visible)

    def mensaje(self, texto, ms=5000):
        """Aviso temporal en la barra del timeline (Fusion no tiene barra de estado)."""
        self._mostrar_estado(texto)
        self._t_mensaje.start(ms)

    def info_seleccion(self, texto):
        """Medidas de lo elegido abajo a la derecha, como Fusion ("1 línea de boceto | Longitud: 123.698 mm").
        Con texto vacío vuelve el resumen del documento."""
        self._info_sel = texto or ""
        if self._info_sel:
            self._t_mensaje.stop()              # elegir algo es lo último que hizo el usuario: manda sobre un aviso
        if not self._t_mensaje.isActive():
            self._mostrar_estado(self._info_sel or self._texto_estado)

    def aviso_flotante(self, texto, nivel="advertencia", detalle=None):
        """Aviso abajo a la derecha de la vista ("1 advertencia(s)" + texto + "Más información")."""
        self.area.toast.mostrar(texto, nivel, detalle)

    def _anunciar_avisos(self):
        """Cuando un paso del timeline pasa a tener aviso o error, lo anuncia con el aviso flotante."""
        actuales = {(i, r.estado, r.mensaje) for i, r in enumerate(self.doc.resultados) if r.estado in ("aviso", "error")}
        nuevos = sorted(actuales - (self._avisos_vistos or set()))
        primera = self._avisos_vistos is None
        self._avisos_vistos = actuales
        if nuevos and not primera:
            i, estado, texto = nuevos[-1]
            nombre = self.doc.operaciones[i].nombre if i < len(self.doc.operaciones) else ""
            self.aviso_flotante(texto or "El paso no se pudo calcular.", "error" if estado == "error" else "advertencia",
                                f"{nombre}: {texto}" if nombre else texto)

    def _mostrar_estado(self, texto):
        etiqueta = self.timeline.estado
        etiqueta.setToolTip(texto)
        etiqueta.setText(etiqueta.fontMetrics().elidedText(texto, Qt.ElideMiddle, 560))

    # ------------------------------------------------------------ documento
    def set_documento(self, doc):
        if self.modo_boceto.activo:
            self._cerrar_panel_de_boceto()
            self.modo_boceto.cancelar()
        self._cancelar_eleccion()
        self.doc = doc
        self._avisos_vistos = None
        self.ocultos = set()
        self.patron_activo = None
        self.vis = dict(VISIBILIDAD_INICIAL)
        doc.suscribir(self._actualizar)
        self._actualizar()
        if hasattr(self, "comentarios"):
            self.comentarios.set_documento(doc)
        QTimer.singleShot(0, self.visor, self.visor.encuadrar)

    def _actualizar(self):
        estado = self.doc.estado_final
        self._refrescar_visibilidad()
        self.timeline.actualizar(self.doc)
        modificado = " *" if self.doc.modificado else ""
        self.setWindowTitle(f"{self.doc.nombre}{modificado} — {NOMBRE_APP} {VERSION}")
        self.pestana_doc.setText(f"{self.doc.nombre}{modificado}")
        self.acciones["deshacer"].setEnabled(self.doc.puede_deshacer())
        self.acciones["rehacer"].setEnabled(self.doc.puede_rehacer())
        errores = sum(1 for r in self.doc.resultados if r.estado == "error")
        avisos = sum(1 for r in self.doc.resultados if r.estado == "aviso")
        texto = f"{len(estado.cuerpos)} cuerpo(s) · {len(self.doc.operaciones)} paso(s)"
        if errores:
            texto += f" · ⚠ {errores} con error"
        if avisos:
            texto += f" · {avisos} con aviso"
        self._texto_estado = texto
        if hasattr(self, "comentarios") and self.comentarios.doc is self.doc:
            self.comentarios.actualizar()
            self.area.reubicar()
        if not self._t_mensaje.isActive():
            self._mostrar_estado(self._info_sel or texto)
        self._anunciar_avisos()

    def _estado_visible(self):
        """Mientras se edita un boceto, el modelo se ve como estaba en ese paso (como Fusion). Con un
        comando abierto se ve su vista previa."""
        if self._estado_previa is not None:
            return self._estado_previa
        if self.modo_boceto.activo and self._indice_boceto is not None:
            return self.doc.estado_en(self._indice_boceto)
        return self.doc.estado_final

    def _ocultos_efectivos(self, estado):
        ocultos = set(self.ocultos)
        if not (self.vis["todo"] and self.vis["cuerpos"]):
            ocultos |= set(estado.cuerpos)
        if not (self.vis["todo"] and self.vis["bocetos"]):
            ocultos |= set(estado.bocetos)
        patrones = {cid for cid, c in estado.cuerpos.items() if es_patron_plano(c)}
        if self.patron_activo in patrones:  # como Fusion: el patrón plano solo, en su propio modo
            ocultos |= (set(estado.cuerpos) - {self.patron_activo}) | set(estado.bocetos)
            ocultos.discard(self.patron_activo)
        else:                               # en el modelo plegado el patrón plano no se ve
            ocultos |= patrones
        return ocultos

    def _refrescar_visibilidad(self):
        if self.patron_activo is not None and self.patron_activo not in self.doc.estado_final.cuerpos:
            self._poner_patron_activo(None)     # lo borraron o se deshizo: vuelve el modelo plegado
            return
        estado, c = self._estado_visible(), self.visor.config
        base = self.vis["todo"] and self.vis["origen"]
        c.origen = {clave.strip("_"): base and clave not in self.ocultos for clave, _, _ in ORIGEN}
        construccion = self.vis["todo"] and self.vis["planos"]
        c.planos_usuario = [(ident, pl.nombre, pl) for ident, pl in estado.planos.items()
                            if construccion and ident not in self.ocultos]
        c.ejes_usuario = [(ident, nombre, (p, d)) for ident, (p, d, nombre) in estado.ejes.items()
                          if construccion and ident not in self.ocultos]
        c.puntos_usuario = [(ident, nombre, p) for ident, (p, nombre) in estado.puntos.items()
                            if construccion and ident not in self.ocultos]
        c.lienzos = [(ident, datos) for ident, datos in estado.lienzos.items()
                     if self.vis["todo"] and ident not in self.ocultos]
        activo = self.modo_boceto.datos.get("op") if self.modo_boceto.activo else None
        excluir = (activo.id,) if activo is not None else ()
        ocultos = frozenset(self._ocultos_efectivos(estado))
        apariencias = self._apariencias(estado)
        if self.prefs_colores_componente:
            from .visor3d import PALETA
            apariencias = {cid: PALETA[i % len(PALETA)] for i, cid in enumerate(estado.cuerpos)}
        for v in self.area.visores:
            v.opacidad = {cid: props["opacidad"] for cid, props in self.doc.propiedades.items() if "opacidad" in props}
            v.set_modelo(estado, ocultos, excluir, apariencias)
        if self.panel is None or not self.panel.comando.SIN_OP:
            self.aplicar_analisis(estado)
        titulo = self.doc.nombre if self.doc.ruta else "(Sin guardar)"
        self.navegador.analisis = [(f"analisis:{n}", n, a.get("visible", True)) for n, a in self.doc.analisis.items()]
        self.navegador.componentes = [
            (k, comp["nombre"], comp.get("fijo", False),
             [(c.id, self.nombre_cuerpo(c)) for c in estado.cuerpos.values() if c.componente == k])
            for k, comp in estado.componentes.items()]
        self.navegador.uniones = [(k, u["nombre"]) for k, u in estado.uniones.items()]
        self.navegador.lienzos = [(k, d["nombre"], k not in self.ocultos) for k, d in estado.lienzos.items()]
        self.navegador.actualizar(titulo, [(k.id, self.nombre_cuerpo(k)) for k in estado.cuerpos.values()
                                           if not k.componente],
                                  [(b.op_id, b.nombre, "boceto_bloqueado" if b.boceto.curvas and b.solver is not None
                                    and b.solver.totalmente_restringido else "boceto")
                                   for b in estado.bocetos.values()], self.ocultos, self.vis,
                                  [(i, pl.nombre, "plano_desfase") for i, pl in estado.planos.items()] +
                                  [(i, n, "eje_arista") for i, (_p, _d, n) in estado.ejes.items()] +
                                  [(i, n, "punto_vertice") for i, (_p, n) in estado.puntos.items()],
                                  list(self.doc.vistas))

    def aplicar_analisis(self, estado=None):
        """Dibuja los análisis visibles del navegador (sección, cebra, curvatura…) sobre el modelo."""
        from . import analisis_vista
        estado = estado or self._estado_visible()
        resultados = []
        for nombre, a in self.doc.analisis.items():
            if not a.get("visible", True):
                continue
            try:
                resultados.append(analisis_vista.calcular(a["tipo"], a["params"], estado))
            except Exception as e:  # noqa: BLE001 — un análisis cuya referencia se perdió no rompe la vista
                log.warning("Análisis %s: %s", nombre, e)
        analisis_vista.aplicar(self.visor, analisis_vista.combinar(resultados))

    def _apariencias(self, estado):
        """Color de cada cuerpo según Aspecto o, si no tiene, según su Material físico (como Fusion)."""
        from ..nucleo.analisis import TABLA_MATERIALES
        salida = {}
        for cid, c in estado.cuerpos.items():
            props = propiedades_cuerpo(self.doc.propiedades, c)
            if props.get("apariencia"):
                salida[cid] = tuple(props["apariencia"])
            elif props.get("material") in TABLA_MATERIALES:
                salida[cid] = TABLA_MATERIALES[props["material"]]["color"]
        return salida

    def nombre_cuerpo(self, cuerpo):
        return self.doc.propiedad(cuerpo.id, "nombre") or cuerpo.nombre

    # ------------------------------------------------------------ ensamblajes: animar e insertar
    def animar_union(self, op_id, desde=None, hasta=None, segundos=3.0):
        """Anima una unión sin recalcular el modelo (como «Animar unión» del navegador de Fusion): mueve el
        dibujo de los cuerpos de sus componentes alrededor (o a lo largo) del eje de la unión."""
        from ..timeline.ops_ensamblar import MOVIMIENTOS, movimiento
        estado = self.doc.estado_final
        u = estado.uniones.get(op_id)
        if u is None:
            self.mensaje("Esa unión no está calculada (¿suprimida o después del marcador?).")
            return
        giros, desliz = MOVIMIENTOS[u["tipo"]]
        if not giros and not desliz:
            self.mensaje("Una unión rígida no tiene movimiento para animar.")
            return
        cuerpos = [c for c, cu in estado.cuerpos.items() if (cu.componente or "") in u["componentes"]]
        F = np.asarray(u["marco"], float)
        tam = max((np.linalg.norm(np.subtract(*reversed(geo.caja_envolvente(estado.cuerpos[c].forma))))
                   for c in cuerpos), default=50.0)
        desde = 0.0 if desde is None else desde
        hasta = (360.0 if giros else tam) if hasta is None else hasta
        clave = "giro" if giros else "desliz"
        inicio = time.perf_counter()

        def paso():
            t = (time.perf_counter() - inicio) / segundos
            if t >= 1.0 or not self.isVisible():
                self._t_anim.stop()
                self.visor.transformaciones = {}
                self.visor.update()
                return
            fase = t if giros else (0.5 - abs(t - 0.5)) * 2      # el deslizamiento va y vuelve
            valores = dict.fromkeys(giros + desliz, 0.0)
            valores[clave] = desde + (hasta - desde) * fase
            m = F @ movimiento(u["tipo"], valores, u["eje_giro"], u["eje_desliz"]) @ np.linalg.inv(F)
            self.visor.transformaciones = dict.fromkeys(cuerpos, m)
            self.visor.update()

        if not hasattr(self, "_t_anim"):
            self._t_anim = QTimer(self, interval=33)
        try:
            self._t_anim.timeout.disconnect()
        except (RuntimeError, TypeError):
            pass
        self._t_anim.timeout.connect(paso)
        self._t_anim.start()

    def _estudio_movimiento(self):
        uniones = {k: u["nombre"] for k, u in self.doc.estado_final.uniones.items()}
        if not uniones:
            QMessageBox.information(self, NOMBRE_APP, "Todavía no hay uniones para animar.")
            return
        nombre, ok = QInputDialog.getItem(self, "Estudio de movimiento", "Unión a animar:", list(uniones.values()), 0,
                                          False)
        if ok:
            self.animar_union(next(k for k, n in uniones.items() if n == nombre))

    # ------------------------------------------------------------ otros espacios de trabajo
    @staticmethod
    def _clase_espacio(clave):
        """Ventana de cada espacio de trabajo (si el módulo existe)."""
        try:
            if clave == "dibujo":
                from .dibujo import VentanaDibujo
                return VentanaDibujo
            if clave == "render":
                from .render import VentanaRender
                return VentanaRender
            if clave == "animacion":
                from .animacion import VentanaAnimacion
                return VentanaAnimacion
        except Exception as e:  # noqa: BLE001 — un espacio roto no tiene que impedir abrir el diseño
            log.warning("Espacio de trabajo %s no disponible: %s", clave, e)
            return None
        return None

    def abrir_espacio(self, clave, vista_base=True):
        """Abre (o trae al frente) DIBUJO, RENDERIZAR o ANIMACIÓN para el diseño actual. Lo que se hace en
        esas ventanas se guarda con el proyecto (`doc.espacios`)."""
        if not self._salir_de_boceto():
            return None
        if not self.doc.estado_final.cuerpos:
            QMessageBox.information(self, NOMBRE_APP, "El diseño todavía no tiene cuerpos.")
            return None
        v = self._espacios.get(clave)
        if v is None or v.doc is not self.doc:
            clase = self._clase_espacio(clave)
            v = clase(self.doc, self)
            datos = self.doc.espacios.get(clave)
            if datos and hasattr(v, "desde_dict"):
                try:
                    v.desde_dict(datos)
                except (KeyError, ValueError, TypeError) as e:
                    log.warning("No se pudo restaurar %s: %s", clave, e)
            if hasattr(v, "cambiado") and hasattr(v, "a_dict"):
                v.cambiado.connect(lambda c=clave, w=v: self._guardar_espacio(c, w))
            self._espacios[clave] = v
            if clave == "dibujo" and not datos and vista_base:
                QTimer.singleShot(0, lambda: v.comando("vista_base"))   # Fusion pide la vista base al crear el plano
        v.show()
        v.raise_()
        v.activateWindow()
        return v

    def _guardar_espacio(self, clave, ventana):
        self.doc.espacios[clave] = ventana.a_dict()
        self.doc.modificado = True

    # ------------------------------------------------------------ ADMINISTRAR / CONFIGURAR / UTILIDADES
    def lista_materiales(self):
        from .administrar import DialogoListaMateriales
        if not self._salir_de_boceto():
            return
        DialogoListaMateriales(self.doc, self, nombre_de=self.nombre_cuerpo).exec()

    def configurar(self):
        from .administrar import DialogoConfiguraciones
        if not self._salir_de_boceto():
            return
        dlg = DialogoConfiguraciones(self.doc, self)
        if dlg.exec():
            self._intentar(lambda: self.doc.aplicar_configuracion(dlg.datos()))
            if self.doc.configuraciones.get("activa"):
                self.mensaje(f"Configuración activa: {self.doc.configuraciones['activa']}", 5000)

    def secuencias(self):
        from .administrar import DialogoScripts
        DialogoScripts(self).exec()

    def biblioteca_roscas(self):
        from .administrar import DialogoRoscas
        DialogoRoscas(self).exec()

    def operacion_base(self):
        """Crear operación base: los cuerpos elegidos quedan como un paso fijo (B-rep guardado), sin depender
        de los pasos anteriores (modelado directo dentro de un diseño paramétrico)."""
        from .comandos.modificar import _cuerpos as ids_de
        cuerpos = ids_de(self.seleccion) if self.seleccion else []
        if not cuerpos:
            QMessageBox.information(self, NOMBRE_APP, "Elegí en la vista los cuerpos (clic en uno; Ctrl+clic para más) "
                                    "y volvé a usar «Crear operación base».")
            return
        from ..timeline.operaciones import OpOperacionBase
        estado = self.doc.estado_final
        self._seleccionar([])
        self._agregar(OpOperacionBase.desde_cuerpos(self.doc.nuevo_id(), [estado.cuerpos[c] for c in cuerpos]))

    def _insertar_archivo(self, clase):
        """INSERTAR › DXF / SVG / imagen / lienzo: primero el archivo, después el diálogo para ubicarlo en un plano
        (con un boceto abierto, DXF, SVG e imagen van a ESE boceto: ver `ejecutar_comando`)."""
        ext = clase.EXTENSIONES
        ruta, _ = QFileDialog.getOpenFileName(self, clase.TITULO, "", f"{ext[0].upper()} (" +
                                              " ".join(f"*.{e}" for e in ext) + ")")
        if ruta:
            self.ejecutar_comando(clase(), valores={"archivo": ruta})

    def guardar_boceto_dxf(self, op_id):
        from ..io_archivos.boceto_archivos import primitivas_dxf_de_boceto
        from ..io_archivos.dxf import ErrorDXF, escribir_dxf
        br = self.doc.estado_final.bocetos.get(op_id)
        if br is None:
            return
        ruta, _ = QFileDialog.getSaveFileName(self, "Guardar como DXF", f"{br.nombre}.dxf", "DXF (*.dxf)")
        if not ruta:
            return
        try:
            escribir_dxf(ruta, primitivas_dxf_de_boceto(br.boceto, incluir_construccion=True),
                         capas={"CONSTRUCCION": {"color": 30, "tipo": "trazos"}})
            self.mensaje(f"Boceto guardado en {ruta}", 5000)
        except (ErrorDXF, OSError) as e:
            QMessageBox.critical(self, "No se pudo guardar", str(e))

    def guardar_boceto_svg(self, op_id):
        """Boceto → SVG en milímetros (corte láser, vinilo); la construcción va en un grupo aparte."""
        from ..io_archivos.svg import ErrorSVG, escribir_svg
        br = self.doc.estado_final.bocetos.get(op_id)
        if br is None:
            return
        ruta, _ = QFileDialog.getSaveFileName(self, "Guardar como SVG", f"{br.nombre}.svg", "SVG (*.svg)")
        if not ruta:
            return
        try:
            construccion = [c.id for c in br.boceto.curvas.values() if c.construccion]
            escribir_svg(ruta, br.boceto.geometria(incluir_construccion=True), construccion)
            self.mensaje(f"Boceto guardado en {ruta}", 5000)
        except (ErrorSVG, OSError) as e:
            QMessageBox.critical(self, "No se pudo guardar", str(e))

    def limpiar_boceto(self, op_id):
        """Quita curvas repetidas, cierra huecos de 0,01 mm y junta líneas alineadas (lo típico de un DXF/SVG)."""
        op = next((o for o in self.doc.operaciones if o.id == op_id), None)
        if op is None or not hasattr(op, "boceto"):
            return
        nueva = op.copia()
        hecho = nueva.boceto.limpiar(0.01)
        if not any(hecho.values()):
            self.mensaje(f"{op.nombre}: no había nada para limpiar.", 5000)
            return
        self._reemplazar(nueva)
        self.mensaje(f"{op.nombre}: {hecho['duplicadas']} repetidas borradas, {hecho['huecos']} huecos cerrados, "
                     f"{hecho['colineales']} líneas unidas.", 8000)

    def insertar_diseno(self):
        from ..timeline.ops_ensamblar import OpInsertarDiseno
        if not self._salir_de_boceto():
            return
        ruta, _ = QFileDialog.getOpenFileName(self, "Insertar componente", "", FILTRO_PROYECTO)
        if not ruta:
            return
        try:
            otro = proyecto.abrir(ruta)
        except (proyecto.ErrorProyecto, OSError, ValueError, KeyError) as e:
            QMessageBox.critical(self, "No se pudo insertar", str(e))
            return
        self._agregar(OpInsertarDiseno(self.doc.nuevo_id(), f"Insertar {Path(ruta).stem}", archivo=Path(ruta).stem,
                                       receta=otro.a_dict()))

    def _colores_componente(self, activo):
        self.prefs_colores_componente = bool(activo)
        self._refrescar_visibilidad()

    def _ojo(self, clave):
        if clave.startswith("analisis:"):
            self.doc.alternar_analisis(clave.split(":", 1)[1])
            return
        especiales = {"__raiz__": "todo", "__origen__": "origen", "__planos__": "planos", "__cuerpos__": "cuerpos",
                      "__bocetos__": "bocetos"}
        if clave in especiales:
            self.vis[especiales[clave]] = not self.vis[especiales[clave]]
        elif clave in self.ocultos:
            self.ocultos.discard(clave)
        else:
            self.ocultos.add(clave)
        self._refrescar_visibilidad()

    # ------------------------------------------------------------ selección sin comando (preselección)
    # selección por región, prioridades y filtros (grupo SELECCIONAR)
    PRIORIDAD_FILTROS = {"cuerpo": {"cuerpo"}, "cara": {"cara"}, "arista": {"arista"}, "componente": {"cuerpo"}}
    FILTROS_GRUPO = {"caras": {"cara"}, "aristas": {"arista"}, "vertices": {"vertice"}, "cuerpos": {"cuerpo"},
                     "bocetos": {"perfil", "curva_boceto"}, "construccion": {"plano", "eje", "punto"}}

    def filtro_actual(self):
        """Filtro de selección sin comando: la prioridad manda; si no hay, los filtros marcados."""
        prioridad = getattr(self, "prioridad_seleccion", None)
        if prioridad:
            return set(self.PRIORIDAD_FILTROS[prioridad])
        activos = getattr(self, "grupos_filtro", None)
        if activos is None:
            return set(FILTRO_SELECCION)
        return set().union(*(self.FILTROS_GRUPO[g] for g in activos)) or {"cuerpo"}

    def _aplicar_filtro(self):
        if self.panel is None:
            self.visor.set_filtro(self.filtro_actual())

    def _prioridad(self, clave):
        actual = getattr(self, "prioridad_seleccion", None)
        self.prioridad_seleccion = None if actual == clave else clave
        for c in self.PRIORIDAD_FILTROS:
            self.acciones[f"prioridad_{c}"].setChecked(self.prioridad_seleccion == c)
        self._aplicar_filtro()

    def _filtro_seleccion(self, grupo, activo):
        if getattr(self, "grupos_filtro", None) is None:
            self.grupos_filtro = set(self.FILTROS_GRUPO)
        (self.grupos_filtro.add if activo else self.grupos_filtro.discard)(grupo)
        self._aplicar_filtro()

    def accion_seleccionar(self, _=False):
        """SELECCIONAR › Seleccionar (como la flecha de Fusion): deja de dibujar y vuelve a elegir. Dentro de un
        boceto sale de la herramienta activa (antes solo salía de órbita, encuadre y zoom y la herramienta de
        boceto seguía dibujando); afuera, también corta la elección de plano pendiente."""
        self.visor.set_modo(None)
        if self.modo_boceto.activo:
            self.modo_boceto.herramienta("seleccionar")
        else:
            self._cancelar_eleccion()

    def _modo_seleccion(self, modo):
        if self.panel is not None or not self._salir_de_boceto():
            return
        self.visor.set_modo(None if self.visor.modo == modo else modo)
        self.visor.setFocus()

    def _hits_cuerpos(self, ids):
        from .comando import hit_desde_ref
        estado = self._estado_visible()
        return [hit_desde_ref({"tipo": "cuerpo", "cuerpo": c}, estado) for c in ids]

    def _seleccion_region(self, poligono, cruce):
        """Selección en ventana o de forma libre: cuerpos (o caras con prioridad de cara) dentro del polígono."""
        estado = self._estado_visible()
        caras = getattr(self, "prioridad_seleccion", None) == "cara"
        nuevos = []
        for m in self.visor._mallas:
            if caras:
                lista, tris, indice = self.visor._datos_pick(m["id"])
                for i, cara in enumerate(lista):
                    pts = tris[indice == i].reshape(-1, 3)
                    s, ok = self.visor.puntos_pantalla(pts)
                    dentro = dentro_del_poligono(s[ok], poligono) if ok.any() else np.zeros(0, bool)
                    if len(dentro) and (dentro.any() if cruce else dentro.all()):
                        from ..nucleo import referencias as refs
                        from .comando import hit_desde_ref
                        nuevos.append(hit_desde_ref(refs.referencia(m["id"], cara, estado.cuerpos[m["id"]].forma),
                                                    estado))
                continue
            v = m["v"][:: max(1, len(m["v"]) // 400)]
            s, ok = self.visor.puntos_pantalla(v)
            dentro = dentro_del_poligono(s[ok], poligono) if ok.any() else np.zeros(0, bool)
            if len(dentro) and (dentro.any() if cruce else dentro.all()):
                nuevos.append(m["id"])
        if not caras:
            nuevos = self._hits_cuerpos(self._expandir_componentes(nuevos))
        aditivo = bool(QApplication.keyboardModifiers() & (Qt.ControlModifier | Qt.ShiftModifier))
        refs_previas = [h["ref"] for h in self.seleccion]
        self._seleccionar((self.seleccion if aditivo else []) +
                          [h for h in nuevos if not aditivo or h["ref"] not in refs_previas])

    def _expandir_componentes(self, ids):
        if getattr(self, "prioridad_seleccion", None) != "componente":
            return ids
        estado = self._estado_visible()
        comps = {estado.cuerpos[c].componente for c in ids if estado.cuerpos[c].componente}
        return list(dict.fromkeys(ids + [c for c, cu in estado.cuerpos.items() if cu.componente in comps]))

    def _entidad_pintada(self, hit):
        if self.panel is not None:
            return
        if all(h["ref"] != hit["ref"] for h in self.seleccion):
            self._seleccionar(self.seleccion + [hit])

    def _seleccionar_todo(self):
        if self.panel is None and not self.modo_boceto.activo:
            self._seleccionar(self._hits_cuerpos([m["id"] for m in self.visor._mallas]))

    def _invertir_seleccion(self):
        elegidos = {h["ref"].get("cuerpo") for h in self.seleccion if h["tipo"] == "cuerpo"}
        self._seleccionar(self._hits_cuerpos([m["id"] for m in self.visor._mallas if m["id"] not in elegidos]))

    def _seleccion_nombre(self):
        estado = self._estado_visible()
        nombres = {self.nombre_cuerpo(c): c.id for c in estado.cuerpos.values()}
        if not nombres:
            return
        texto, ok = QInputDialog.getText(self, "Seleccionar por nombre", "Nombre (o parte, * = todos):")
        if ok:
            t = texto.strip().lower().replace("*", "")
            self._seleccionar(self._hits_cuerpos([cid for n, cid in nombres.items() if t in n.lower()]))

    def _seleccion_tamano(self):
        minimo, ok = QInputDialog.getDouble(self, "Seleccionar por tamaño", "Tamaño mínimo (diagonal, mm):", 0, 0, 1e6, 2)
        if not ok:
            return
        maximo, ok = QInputDialog.getDouble(self, "Seleccionar por tamaño", "Tamaño máximo (diagonal, mm):", 1000, 0,
                                            1e6, 2)
        if not ok:
            return
        estado = self._estado_visible()
        ids = []
        for m in self.visor._mallas:
            v = m["v"]
            diag = float(np.linalg.norm(v.max(axis=0) - v.min(axis=0))) if len(v) else 0.0
            if minimo <= diag <= maximo and m["id"] in estado.cuerpos:
                ids.append(m["id"])
        self._seleccionar(self._hits_cuerpos(ids))

    def _seleccionar(self, hits):
        self.seleccion = list(hits)
        prims = [p for h in self.seleccion for p in (h.get("dibujo") or [])]
        self.visor.set_capa("preseleccion", prims)
        from .medidas import texto_medidas
        self.info_seleccion(texto_medidas(self.seleccion, self._estado_visible()))

    def _clic_en_vista(self, hit):
        if self.panel is not None or self.modo_boceto.activo:
            return
        mods = QApplication.keyboardModifiers()
        if mods & (Qt.ControlModifier | Qt.ShiftModifier):
            ya = next((h for h in self.seleccion if h["ref"] == hit["ref"]), None)
            self._seleccionar([h for h in self.seleccion if h is not ya] if ya else self.seleccion + [hit])
        else:
            self._seleccionar([hit])

    def _tecla_suprimir(self):
        """Supr: con algo elegido lo borra enseguida (como Fusion); si no, abre el diálogo Suprimir."""
        if self.seleccion and self.panel is None:
            self.suprimir_seleccion()
        else:
            from .comandos.modificar import Suprimir
            self.ejecutar_comando(Suprimir())

    def suprimir_seleccion(self):
        if self.panel is not None or self.modo_boceto.activo:
            return
        borrables = [h for h in self.seleccion if h["tipo"] in ("cuerpo", "cara")]
        if borrables:
            from .comandos.modificar import Suprimir
            from .comando import ContextoComando
            sel, self.seleccion = borrables, []
            self._seleccionar([])
            try:
                Suprimir().aplicar({"objetos": sel}, ContextoComando(self.doc, self))
            except (ValueError, RuntimeError) as e:
                QMessageBox.warning(self, NOMBRE_APP, str(e))

    # ------------------------------------------------------------ menú radial (marking menu de Fusion)
    def _items_radial(self):
        """Los 8 comandos del primer nivel, en el orden de la referencia de Fusion (horario desde arriba):
        Repetir, Pulsar/Tirar, Rehacer, Agujero, Boceto ▸, Mover/copiar, Deshacer, Suprimir. Con un comando
        o una herramienta de boceto activos, a la derecha queda Aceptar y a la izquierda Cancelar."""
        from .menu_radial import ItemRadial as I
        acc = self.acciones

        def de_accion(clave):
            a = acc[clave]
            return I(a.text().split("\t")[0], a.trigger, a.icon(), a.isEnabled())

        ultimo = self._ultimo_comando
        repetir = I(f"Repetir {ultimo.TITULO}" if ultimo else "Repetir", (lambda: self.ejecutar_comando(ultimo()))
                    if ultimo else None, icono(ultimo.ICONO) if ultimo else None, ultimo is not None)
        items = [repetir, de_accion("pulsar_tirar"), de_accion("rehacer"), de_accion("agujero"),
                 I("Boceto", None, icono("boceto"), True, sub=self._items_radial_boceto()), de_accion("mover_copiar"),
                 de_accion("deshacer"), I("Suprimir", self._tecla_suprimir, icono("suprimir"))]
        if self.panel is not None:
            panel = self.panel
            items = [None] * 8
            items[2] = I("Aceptar", panel.aceptar, icono("terminar"))
            items[6] = I("Cancelar", panel.cancelar, icono("cancelar"))
        elif self.modo_boceto.activo and self.modo_boceto.lienzo.herramienta != "seleccionar":
            lienzo = self.modo_boceto.lienzo
            items[2] = I("Aceptar", lambda: self.modo_boceto.herramienta("seleccionar"), icono("terminar"))
            items[6] = I("Cancelar", lienzo.cancelar, icono("cancelar"))
        return items

    def _items_radial_boceto(self):
        """Segundo nivel (comandos de boceto), como Fusion: Terminar boceto, Rectángulo de 2 puntos, Spline,
        Proyectar, Línea, Desfase, Cota de boceto y Círculo de centro y diámetro."""
        from .menu_radial import ItemRadial as I
        mb = self.modo_boceto

        def herramienta(clave):
            a = mb.acciones[clave]
            return I(a.text().split("\t")[0], lambda: self._herramienta_boceto(clave), a.icon(), True)

        return [I("Terminar boceto", mb.terminar, icono("terminar"), mb.activo), herramienta("sk_rectangulo"),
                herramienta("sk_spline_ajuste"), herramienta("sk_proyectar"), herramienta("sk_linea"),
                herramienta("sk_desfase"), herramienta("sk_cota"), herramienta("sk_circulo")]

    def _herramienta_boceto(self, clave):
        """Herramienta de boceto desde el menú radial: fuera del boceto primero pide el plano (como Fusion)."""
        if self.modo_boceto.activo:
            self.modo_boceto.acciones[clave].trigger()
        else:
            self.crear_boceto()
            self._herramienta_pendiente = clave

    def _contexto_radial(self):
        """Lista de debajo del menú radial: comandos según lo elegido, vista, aislar y espacios de trabajo."""
        from .comandos import CATALOGO
        filas = []
        tipos = {h["tipo"] for h in self.seleccion}
        if "cara" in tipos and any(h.get("plano") is not None for h in self.seleccion):
            filas.append(("Crear boceto", self._boceto_en_seleccion))
        sugeridos = []
        if "cara" in tipos:
            sugeridos += ["pulsar_tirar", "desfase_cara", "vaciado", "aspecto", "medir"]
        if "arista" in tipos:
            sugeridos += ["empalme_3d", "chaflan_3d", "medir"]
        if "perfil" in tipos:
            sugeridos += ["extruir", "revolucion"]
        if "cuerpo" in tipos:
            sugeridos += ["mover_copiar", "aspecto", "material_fisico", "quitar"]
        for clave in dict.fromkeys(sugeridos):
            if clave in CATALOGO:
                clase = CATALOGO[clave]
                filas.append((clase.TITULO, lambda c=clase: self.ejecutar_comando(c()),
                              getattr(clase, "ATAJO", "") or ""))
        if self.seleccion:
            filas.append(("Borrar la selección", lambda: self._seleccionar([])))
        if filas:
            filas.append(None)
        cuerpos = [h["ref"].get("cuerpo") for h in self.seleccion if h["tipo"] == "cuerpo"]
        if len(cuerpos) == 1:
            filas.append(("Aislar", lambda c=cuerpos[0]: self._accion_navegador("aislar", c)))
        if self.ocultos:
            filas.append(("Anular aislamiento", lambda: self._accion_navegador("desaislar", None)))
        filas += [("Mirar a", lambda: self.barra_nav.mirar_a() if hasattr(self.barra_nav, "mirar_a") else None),
                  ("Ajustar", self.acciones["ajustar"].trigger, "F6")]
        modos = getattr(self.barra_nav, "modos", {})
        for clave, texto in (("encuadre", "Encuadre"), ("zoom", "Zoom"), ("orbita", "Órbita")):
            if clave in modos:
                filas.append((texto, modos[clave].trigger))
        filas.append(None)
        filas += [("Renderizar", lambda: self.abrir_espacio("render")),
                  ("Animación", lambda: self.abrir_espacio("animacion")),
                  ("Dibujo", lambda: self.abrir_espacio("dibujo"))]
        return filas

    def _menu_vista(self, hit, pos_global):
        """Clic derecho en la vista: el menú radial de Fusion con la lista de contexto debajo."""
        if (hit is not None and self.panel is None and not self.modo_boceto.activo
                and all(h["ref"] != hit["ref"] for h in self.seleccion)):
            self._seleccionar([hit])
        return self.abrir_menu_radial(pos_global)

    def abrir_menu_radial(self, pos_global):
        from .menu_radial import MenuRadial
        contexto = [] if self.panel is not None else self._contexto_radial()
        menu = MenuRadial(self._items_radial(), contexto, self)
        menu.abrir(pos_global)
        self._menu_radial = menu
        return menu

    def _gesto_radial(self, indice):
        """Clic derecho + arrastrar hacia un comando + soltar: lo ejecuta sin mostrar el menú."""
        item = self._items_radial()[indice]
        if item is not None and item.activo and item.funcion is not None and not item.sub:
            item.funcion()

    # ------------------------------------------------------------ "Seleccionar otro" (pulsación larga)
    NOMBRES_ENTIDAD = {"cara": "Cara", "arista": "Arista", "vertice": "Vértice", "cuerpo": "Cuerpo", "perfil": "Perfil",
                       "curva_boceto": "Curva de boceto", "punto_boceto": "Punto de boceto", "plano": "Plano",
                       "eje": "Eje", "punto": "Punto", "boceto": "Boceto"}

    def nombre_entidad(self, hit):
        """Texto para la lista de "Seleccionar otro": "Cara (Cuerpo1)", "Plano XY", "Perfil (Boceto1)"…"""
        tipo, ref = hit["tipo"], hit["ref"]
        base = self.NOMBRES_ENTIDAD.get(tipo, tipo)
        cuerpo = self._estado_visible().cuerpos.get(hit.get("cuerpo")) if hit.get("cuerpo") else None
        if tipo == "cuerpo":
            return self.nombre_cuerpo(cuerpo) if cuerpo is not None else base
        if ref.get("id") in ("XY", "XZ", "YZ", "X", "Y", "Z", "O"):
            return f"{base} {ref['id']}" if ref["id"] != "O" else "Origen"
        if ref.get("boceto"):
            try:
                return f"{base} ({self.doc.operaciones[self.doc.indice(ref['boceto'])].nombre})"
            except Exception:  # noqa: BLE001 — un boceto que ya no existe: solo el tipo
                return base
        if ref.get("id") is not None:
            try:
                return self.doc.operaciones[self.doc.indice(ref["id"])].nombre
            except Exception:  # noqa: BLE001
                return base
        return f"{base} ({self.nombre_cuerpo(cuerpo)})" if cuerpo is not None else base

    def _seleccion_otra(self, entidades, pos_global):
        """Lista de lo que hay bajo el cursor; al pasar por cada fila se resalta en la vista y el clic lo
        elige (vale también dentro de un comando, para tomar una cara o un plano tapados)."""
        from .visor3d import AZUL_HOVER
        m = QMenu(self)
        m.addSection("Seleccionar otro")
        for h in entidades:
            dibujo = [(prim[0], prim[1], AZUL_HOVER, prim[3]) for prim in (h.get("dibujo") or [])]
            a = m.addAction(self.nombre_entidad(h))
            a.hovered.connect(lambda dib=dibujo: self.visor.set_capa("seleccion_otra", dib))
            a.triggered.connect(lambda _=False, h=h: self.visor.entidad_elegida.emit(h))
        m.aboutToHide.connect(lambda: self.visor.set_capa("seleccion_otra", None))
        m.popup(pos_global)
        self._menu_otro = m
        return m

    def _boceto_en_seleccion(self):
        hit = next((h for h in self.seleccion if h["tipo"] == "cara" and h.get("plano") is not None), None)
        if hit is None:
            return
        self._seleccionar([])
        if self._salir_de_boceto():
            self._iniciar_boceto(Boceto(), hit["plano"], {"op": None, "plano": "cara", "marco": hit["plano"].marco(),
                                                                "cara": hit["ref"]})

    def _accion_navegador(self, accion, clave):
        """Menú contextual del navegador (como el de Fusion sobre cuerpos, bocetos y construcción)."""
        from .comandos.modificar import Aspecto, MaterialFisico, MoverCopiar, Quitar, Suprimir
        from .comando import hit_desde_ref
        estado = self.doc.estado_final
        if accion == "renombrar_cuerpo" and clave in estado.cuerpos:
            nombre, ok = QInputDialog.getText(self, "Renombrar", "Nombre:", text=self.nombre_cuerpo(estado.cuerpos[clave]))
            if ok and nombre.strip():
                self.doc.set_propiedad([clave], "nombre", nombre.strip())
        elif accion.startswith("opacidad:"):
            pct = int(accion.split(":")[1])
            self.doc.set_propiedad([clave], "opacidad", None if pct >= 100 else pct / 100)
        elif accion == "aislar":
            self.ocultos |= {c for c in estado.cuerpos if c != clave}
            self.ocultos.discard(clave)
            self._refrescar_visibilidad()
        elif accion == "desaislar":
            self.ocultos -= set(estado.cuerpos)
            self._refrescar_visibilidad()
        elif accion == "propiedades":
            self._propiedades(clave)
        elif accion in ("renombrar_paso",):
            self._renombrar(clave)
        elif accion == "buscar_timeline":
            self.timeline.resaltar(clave)
        elif accion == "borrar_paso":
            self._intentar(lambda: self.doc.eliminar(clave))
        elif accion == "boceto_dxf":
            self.guardar_boceto_dxf(clave)
        elif accion == "boceto_svg":
            self.guardar_boceto_svg(clave)
        elif accion == "boceto_limpiar":
            self.limpiar_boceto(clave)
        elif accion == "animar_union":
            self.animar_union(clave)
        elif accion == "accionar_union":
            from .comandos.ensamblar import AccionarUniones
            self.ejecutar_comando(AccionarUniones(), valores={"union": clave})
        elif accion == "fijar_componente":
            from ..timeline.ops_ensamblar import OpComponente
            op = self.doc.operacion(clave)
            if isinstance(op, OpComponente):
                self._reemplazar(OpComponente(op.id, op.nombre, op.suprimida, **dict(op.p, fijo=not op.p.get("fijo"))))
        elif accion == "aislar_componente":
            self.ocultos |= {c for c, cu in estado.cuerpos.items() if cu.componente != clave}
            self.ocultos -= {c for c, cu in estado.cuerpos.items() if cu.componente == clave}
            self._refrescar_visibilidad()
        elif accion == "analisis_borrar":
            self.doc.quitar_analisis(clave.split(":", 1)[1])
        elif accion == "analisis_ojo":
            self.doc.alternar_analisis(clave.split(":", 1)[1])
        elif accion in ("mover", "aspecto", "material", "quitar", "suprimir"):
            clase = {"mover": MoverCopiar, "aspecto": Aspecto, "material": MaterialFisico, "quitar": Quitar,
                     "suprimir": Suprimir}[accion]
            self.ejecutar_comando(clase(), valores={"cuerpos" if accion != "suprimir" else "objetos":
                                                     [hit_desde_ref({"tipo": "cuerpo", "cuerpo": clave}, estado)]})

    def claves_navegador_de(self, op_id):
        """Claves del navegador de lo que crea el paso `op_id` (su boceto, plano, unión, componente o cuerpos); si
        no crea nada propio (empalme, vaciado…), los cuerpos que modifica."""
        estado = self.doc.estado_final
        propias = [op_id] + [k for k in list(estado.planos) + list(estado.ejes) + list(estado.puntos) +
                             list(estado.lienzos) if str(k).split("_")[0] == op_id]
        propias += [c.id for c in estado.cuerpos.values() if c.op_id == op_id]
        if any(self.navegador.item(k) is not None for k in propias):
            return propias
        try:
            deps = self.doc.operacion(op_id).dependencias()
        except Exception:  # noqa: BLE001 — sin dependencias legibles no hay a qué apuntar
            deps = set()
        return [c.id for c in estado.cuerpos.values() if c.op_id in deps]

    def buscar_en_navegador(self, op_id):
        """Timeline › «Buscar en navegador» (Fusion: Find in Browser): despliega el navegador hasta el elemento
        del paso y lo deja elegido. Devuelve la clave encontrada (o None)."""
        clave = next((k for k in self.claves_navegador_de(op_id) if self.navegador.item(k) is not None), None)
        if clave is None:
            op = self.doc.operacion(op_id)
            self.mensaje(f"«{op.nombre}» no tiene un elemento en el navegador (¿suprimido o después del marcador?).")
            return None
        if not self.navegador.isVisible():
            self.acciones["ver_navegador"].setChecked(True)
            self._mostrar_elemento("ver_navegador", True)
        if self.navegador.arbol.isHidden():
            self.navegador.b_plegar.click()          # el navegador estaba plegado: se despliega
        item = self.navegador.item(clave)
        padre = item.parent()
        while padre is not None:
            padre.setExpanded(True)
            padre = padre.parent()
        self.navegador.arbol.setCurrentItem(item)
        self.navegador.arbol.scrollToItem(item)
        self.navegador.ajustar_alto()
        return clave

    def _elegido_en_navegador(self, ident):
        """Con un comando abierto, elegir en el navegador también selecciona (como en Fusion)."""
        from .comando import Seleccion, hit_desde_ref
        if self.panel is None or self.panel.activa is None:
            return False
        estado = self.panel.ctx.estado
        filtros = self.panel.activa.filtros
        if ident in estado.cuerpos and "cuerpo" in filtros:
            ref = {"tipo": "cuerpo", "cuerpo": ident}
        elif ident in estado.bocetos and filtros & {"boceto", "plano"}:
            ref = {"tipo": "boceto", "boceto": ident}
        elif (ident in estado.planos or ident.strip("_").upper() in ("XY", "XZ", "YZ")) and "plano" in filtros:
            ref = {"tipo": "plano", "id": ident if ident in estado.planos else ident.strip("_").upper()}
        elif (ident in estado.ejes or ident.strip("_").upper() in ("X", "Y", "Z")) and "eje" in filtros:
            ref = {"tipo": "eje", "id": ident if ident in estado.ejes else ident.strip("_").upper()}
        elif (ident in estado.puntos or ident == "__o__") and "punto" in filtros:
            ref = {"tipo": "punto", "id": ident if ident in estado.puntos else "O"}
        else:
            return False
        assert isinstance(self.panel.activa, Seleccion)
        self.panel._elegida(hit_desde_ref(ref, estado))
        return True

    def _propiedades(self, ident):
        if self._elegido_en_navegador(ident):
            return
        estado = self.doc.estado_final
        cuerpo = estado.cuerpos.get(ident)
        if cuerpo:
            n = formato.numero
            self.mensaje(f"{cuerpo.nombre}: volumen {n(geo.volumen(cuerpo.forma), miles=True)} mm³ · "
                         f"área {n(geo.area(cuerpo.forma), miles=True)} mm² · "
                         f"{'sólido válido' if geo.es_valida(cuerpo.forma) else '⚠ geometría inválida'}", 10000)
        elif ident in estado.bocetos:
            b = estado.bocetos[ident]
            self.mensaje(f"{b.nombre}: {len(b.perfiles)} perfil(es) cerrado(s). Doble clic para editarlo.", 8000)

    def _intentar(self, funcion):
        try:
            funcion()
        except (ErrorDocumento, ValueError) as e:
            QMessageBox.warning(self, NOMBRE_APP, str(e))

    def _agregar(self, op):
        res = self.doc.agregar(op)
        self._informar(op, res)

    def _reemplazar(self, op):
        res = self.doc.reemplazar(op.id, op)
        self._informar(op, res)

    def _informar(self, op, res):
        if res.estado == "error":
            QMessageBox.warning(self, "La operación tiene un error",
                                f"{op.nombre}: {res.mensaje}\n\nQuedó en el timeline marcada en rojo: "
                                "podés editarla o deshacer (Ctrl+Z).")
        elif res.estado == "aviso":
            self.mensaje(f"Aviso en {op.nombre}: {res.mensaje}", 8000)
        else:
            self.mensaje(f"{op.nombre}: listo.", 4000)

    def _renombrar_desde_navegador(self, tipo, clave, nombre):
        """Nombre nuevo escrito en el lugar en el navegador (doble clic o F2)."""
        if tipo == "cuerpo":
            self._intentar(lambda: self.doc.set_propiedad([clave], "nombre", nombre))
        else:
            self._intentar(lambda: self.doc.renombrar(clave.split("_")[0], nombre))

    def _renombrar(self, op_id):
        op = self.doc.operacion(op_id)
        nombre, ok = QInputDialog.getText(self, "Renombrar", "Nombre:", text=op.nombre)
        if ok and nombre.strip():
            self.doc.renombrar(op_id, nombre.strip())

    def _deshacer(self):
        if self.modo_boceto.activo:
            self.modo_boceto.lienzo.deshacer()
        else:
            self._intentar(self.doc.deshacer)

    def _salir_de_boceto(self):
        """Antes de otro comando: termina el boceto activo (como Fusion), cancela la elección de plano y
        el diálogo de comando abierto."""
        self._cancelar_eleccion()
        if self.panel is not None:
            self.panel.cancelar()
        return self.modo_boceto.terminar() if self.modo_boceto.activo else True

    # ------------------------------------------------------------ diálogos de comando (estilo Fusion)
    def ejecutar_comando(self, comando, op=None, valores=None):
        """Abre el diálogo del comando sobre el lienzo. Con `op` edita ese paso del timeline."""
        if op is None and self.modo_boceto.activo:
            from .comandos.insertar_en_boceto import InsertarEnBoceto, admite
            if admite(comando):                # Insertar SVG / DXF / imagen: al boceto abierto, sin cambiar de plano
                return self._comando_en_boceto(InsertarEnBoceto(comando, self.modo_boceto.lienzo), valores)
        if not self._salir_de_boceto():
            return None
        ctx = ContextoComando(self.doc, self, op)
        motivo = comando.verificar(ctx)
        if motivo:
            QMessageBox.information(self, NOMBRE_APP, motivo)
            return None
        if op is None and valores is None and self.seleccion:
            from .comando import preseleccion
            valores = preseleccion(comando.campos(ctx), self.seleccion) or None
        self._seleccionar([])
        self._ultimo_comando = type(comando) if op is None else self._ultimo_comando
        self.area.set_vistas_multiples(False)
        if op is not None:                     # al editar se ve el modelo como estaba antes de ese paso
            self._estado_previa = ctx.estado
            self._refrescar_visibilidad()
        panel = PanelComando(comando, ctx, self.visor, valores, self.area)
        panel.previa.connect(self._previa_comando)
        panel.aceptado.connect(lambda nueva: self._comando_aceptado(nueva, op is not None))
        panel.cancelado.connect(self._comando_cerrado)
        self.panel = panel
        self.visor.ventana_libre = False
        self.area.set_panel(panel)
        panel.show()
        self.area.reubicar()
        self.visor.setFocus()
        return panel

    def _comando_en_boceto(self, comando, valores=None):
        """Panel de un comando que trabaja DENTRO del boceto abierto (Insertar SVG/DXF/imagen): el boceto sigue
        abierto, el panel queda arriba de su paleta y al aceptar el cambio entra en el boceto (no en el timeline)."""
        self._cancelar_eleccion()
        if self.panel is not None:
            self.panel.cancelar()
        self.modo_boceto.herramienta("seleccionar")     # una herramienta a medio usar no queda colgada debajo
        ctx = ContextoComando(self.doc, self, None)
        panel = PanelComando(comando, ctx, self.visor, valores, self.area)
        panel.aceptado.connect(lambda _op: self._comando_cerrado())
        panel.cancelado.connect(self._comando_cerrado)
        self.panel = panel
        self.visor.ventana_libre = False
        self.area.set_panel(panel)
        panel.show()
        self.area.reubicar()
        return panel

    def _cerrar_panel_de_boceto(self):
        """Si el panel abierto trabaja dentro del boceto (Insertar SVG…), se cancela: el boceto se cierra."""
        if self.panel is not None and getattr(self.panel.comando, "EN_BOCETO_ABIERTO", False):
            self.panel.cancelar()

    def _previa_comando(self, estado):
        if self.panel is None:
            return
        self._estado_previa = estado if estado is not None else self.panel.ctx.estado
        self._refrescar_visibilidad()

    def _comando_cerrado(self):
        panel, self.panel = self.panel, None
        self.visor.ventana_libre = True
        self.visor.set_filtro(self.filtro_actual())
        self._estado_previa = None
        self.area.set_panel(None)
        if panel is not None:
            panel.deleteLater()
        self._refrescar_visibilidad()

    def _comando_aceptado(self, op, edicion):
        self._comando_cerrado()
        if op is None:
            return
        if edicion:
            self._reemplazar(op)
        else:
            self._agregar(op)
            if op.TIPO == "patron_plano":   # como Fusion: al crearlo, el patrón plano queda a la vista
                nuevo = [c.id for c in self.doc.estado_final.cuerpos.values()
                         if c.op_id == op.id and es_patron_plano(c)]
                if nuevo:
                    self._poner_patron_activo(nuevo[0])

    def alternar_patron_plano(self, _=False):
        """Activar patrón plano / Terminar patrón plano de Fusion: muestra solo el patrón plano (el de la chapa
        elegida, o el último creado) y vuelve al modelo plegado con la segunda pulsación."""
        if self.patron_activo is not None:
            self._poner_patron_activo(None)
            return
        estado = self.doc.estado_final
        patrones = [c for c in estado.cuerpos.values() if es_patron_plano(c)]
        elegidos = {h["ref"].get("cuerpo") for h in self.seleccion if h["tipo"] == "cuerpo"}
        propios = [c for c in patrones if c.id in elegidos or c.chapa.get("patron_de") in elegidos]
        elegido = (propios or patrones[-1:] or [None])[0]
        if elegido is None:
            self.mensaje("Este diseño no tiene patrón plano: crealo con CHAPA › Patrón plano.")
        self._poner_patron_activo(elegido.id if elegido is not None else None)

    def _poner_patron_activo(self, cid):
        self.patron_activo = cid
        a = self.acciones["activar_patron_plano"]
        a.setChecked(cid is not None)
        a.setText("Terminar patrón plano" if cid is not None else "Activar patrón plano")
        if cid is not None:
            self.mensaje("Patrón plano: se ve solo el desarrollo. Pulsá «Terminar patrón plano» para volver.")
        self._refrescar_visibilidad()

    # ------------------------------------------------------------ vistas guardadas
    def _vista_nueva(self):
        nombre, ok = QInputDialog.getText(self, "Nueva vista con nombre", "Nombre:",
                                          text=f"Vista {len(self.doc.vistas) + 1}")
        if ok and nombre.strip():
            v = self.visor
            self.doc.vistas[nombre.strip()] = {"objetivo": [float(x) for x in v.objetivo], "distancia": v.distancia,
                                               "R": v.R.tolist(), "camara": v.config.camara}
            self.doc.modificado = True
            self._actualizar()

    def _vista_ir(self, nombre):
        d = self.doc.vistas.get(nombre)
        if d:
            v = self.visor
            v.objetivo, v.distancia, v.R = np.array(d["objetivo"], float), float(d["distancia"]), np.array(d["R"], float)
            v.config.camara = d.get("camara", v.config.camara)
            v.update()

    def _vista_renombrar(self, nombre):
        nuevo, ok = QInputDialog.getText(self, "Renombrar vista", "Nombre:", text=nombre)
        if ok and nuevo.strip() and nuevo.strip() not in self.doc.vistas:
            self.doc.vistas[nuevo.strip()] = self.doc.vistas.pop(nombre)
            self.doc.modificado = True
            self._actualizar()

    def _vista_borrar(self, nombre):
        self.doc.vistas.pop(nombre, None)
        self.doc.modificado = True
        self._actualizar()

    def calcular_todo(self):
        inicio = time.perf_counter()
        self.doc.recalcular(0)
        self.mensaje(f"Calculado todo: {len(self.doc.operaciones)} paso(s) en {time.perf_counter() - inicio:.2f} s")

    # ------------------------------------------------------------ crear / editar operaciones
    def _elegir_plano(self, proposito, aviso):
        if not self._salir_de_boceto():
            return
        self._eleccion = proposito
        self.area.set_vistas_multiples(False)
        self.visor.set_modo("elegir_plano")
        self.visor.setFocus()
        self.area.mostrar_aviso(aviso)

    def _cancelar_eleccion(self):
        if self._eleccion is not None:
            self._eleccion = None
            self.area.mostrar_aviso("")
            if self.visor.modo == "elegir_plano":
                self.visor.set_modo(None)

    def crear_boceto(self):
        self._elegir_plano("boceto", "Seleccione un plano o una cara plana   (Esc: cancelar)")

    def _plano_elegido(self, hit):
        proposito = self._eleccion
        self._cancelar_eleccion()
        if proposito == "boceto":
            self._iniciar_boceto(Boceto(), hit["plano"], {"op": None, "plano": hit["ref"], "marco": hit["marco"],
                                                                "cara": hit.get("cara_ref")})

    def _nombre_nuevo(self, clase, base):
        """Nombres como los de Fusion: Boceto1, Boceto2…, Plano1…"""
        usados = {o.nombre for o in self.doc.operaciones}
        n = sum(1 for o in self.doc.operaciones if isinstance(o, clase)) + 1
        while f"{base}{n}" in usados:
            n += 1
        return f"{base}{n}"

    def _iniciar_boceto(self, boceto, plano, datos, indice=None):
        self._indice_boceto = indice
        self.modo_boceto.iniciar(boceto, plano, datos, mirar=self.prefs["general/auto_mirar_boceto"])
        self.modo_boceto.set_forzar(self.prefs["vista/forzar_rejilla"])
        self._refrescar_visibilidad()
        pendiente, self._herramienta_pendiente = self._herramienta_pendiente, None
        if pendiente in self.modo_boceto.acciones:
            self.modo_boceto.acciones[pendiente].trigger()

    def _boceto_terminado(self, boceto, datos):
        self._cerrar_panel_de_boceto()
        self._indice_boceto = None
        op = datos.get("op")
        if op is None:
            if not boceto.puntos:
                self.mensaje("El boceto quedó vacío: no se agregó al timeline.")
                self._refrescar_visibilidad()
                return
            self._agregar(OpBoceto(self.doc.nuevo_id(), self._nombre_nuevo(OpBoceto, "Boceto"), plano=datos["plano"],
                                   marco=datos["marco"], cara=datos.get("cara"), boceto=boceto))
        else:
            self._reemplazar(OpBoceto(op.id, op.nombre, op.suprimida, boceto=boceto, **op.p))
        self._refrescar_visibilidad()


    def crear_primitiva(self, forma):
        """Prisma rectangular, cilindro, esfera o toroide: abre su comando con panel (`comandos/primitivas.py`)."""
        return self.ejecutar_comando(CATALOGO[forma]())

    def editar_operacion(self, op_id):
        if not self._salir_de_boceto():
            return
        op = self.doc.operacion(op_id)
        if self.doc.indice(op_id) >= self.doc.marcador:
            # Lo que está después del marcador no se calculó: los cuerpos y bocetos que usa no existen
            # todavía y el diálogo mostraría opciones equivocadas (Fusion también avanza el marcador).
            QMessageBox.information(self, NOMBRE_APP, f"«{op.nombre}» está después del marcador del timeline. "
                                    "Mové el marcador a la derecha de este paso para editarlo.")
            return
        clase = None if isinstance(op, OpBoceto) else comando_para(op)
        if clase is not None:
            self.ejecutar_comando(clase(), op=op)
            return
        if isinstance(op, OpBoceto):
            br = self.doc.estado_final.bocetos.get(op.id)
            if br is None:
                QMessageBox.information(self, NOMBRE_APP, f"«{op.nombre}» está suprimido o tiene un error de plano: "
                                        "activalo o corregí su plano de referencia para editarlo.")
                return
            self._iniciar_boceto(op.boceto, br.plano, {"op": op}, self.doc.indice(op.id))
        elif isinstance(op, OpImportarSTEP):
            QMessageBox.information(self, NOMBRE_APP, f"Importación de «{op.p['archivo']}»: no tiene parámetros editables.")

    def parametros(self):
        dlg = DialogoParametros(self.doc.parametros, self)
        if dlg.exec() and dlg.resultado is not None:
            self._intentar(lambda: self.doc.aplicar_parametros(dlg.resultado))
            if self.modo_boceto.activo:          # las cotas del boceto activo usan los parámetros nuevos
                self.modo_boceto.lienzo.resolver()

    # ------------------------------------------------------------ archivos
    def _confirmar_descartar(self):
        if not self.doc.modificado:
            return True
        r = QMessageBox.question(self, NOMBRE_APP, f"«{self.doc.nombre}» tiene cambios sin guardar. ¿Guardar?",
                                 QMessageBox.Save | QMessageBox.Discard | QMessageBox.Cancel)
        if r == QMessageBox.Save:
            return self.guardar()
        if r == QMessageBox.Discard:
            proyecto.borrar_autoguardado(self.doc)
            return True
        return False

    def nuevo(self):
        if self._salir_de_boceto() and self._confirmar_descartar():
            self.set_documento(Documento())

    def abrir(self):
        if not self._salir_de_boceto() or not self._confirmar_descartar():
            return
        ruta, _ = QFileDialog.getOpenFileName(self, "Abrir", "", FILTRO_ABRIR)
        if ruta:
            self.abrir_ruta(ruta)

    def _abrir_reciente(self, ruta):
        if self._confirmar_descartar():
            self.abrir_ruta(ruta)

    def abrir_ruta(self, ruta):
        if abrir_externo.es_externo(ruta):
            self._abrir_externo(ruta)
            return
        try:
            pendiente = proyecto.autoguardado_pendiente(ruta)
            origen = ruta
            if pendiente:
                if QMessageBox.question(self, "Recuperar", "Hay un autoguardado más reciente que el proyecto. "
                                        "¿Abrir el autoguardado? (Si respondés No, se descarta.)") == QMessageBox.Yes:
                    origen = pendiente
                else:
                    pendiente.unlink(missing_ok=True)
            doc = proyecto.abrir(origen)
            doc.ruta, doc.nombre = str(ruta), Path(ruta).stem
            doc.modificado = origen != ruta
            self.set_documento(doc)
            self._recordar(ruta)
        except (proyecto.ErrorProyecto, OSError, ValueError, KeyError) as e:
            QMessageBox.critical(self, "No se pudo abrir", str(e))

    def _abrir_externo(self, ruta):
        """STEP, IGES, mallas, DXF o .f3d/.f3z como documento nuevo (sin ruta: Guardar pide dónde)."""
        unidades = "mm"
        if abrir_externo.pide_unidades(ruta):
            unidades, ok = QInputDialog.getItem(self, "Abrir malla", "Unidades del archivo:",
                                                list(abrir_externo.UNIDADES_MALLA), 0, False)
            if not ok:
                return
        es_fusion = Path(ruta).suffix.lower() in puente_fusion.EXTENSIONES
        try:
            if es_fusion:
                doc, avisos = self._esperando("Leyendo el archivo de Fusion…",
                                              lambda: abrir_externo.documento_desde_archivo(ruta, unidades))
            else:
                QApplication.setOverrideCursor(Qt.WaitCursor)
                try:
                    doc, avisos = abrir_externo.documento_desde_archivo(ruta, unidades)
                finally:
                    QApplication.restoreOverrideCursor()
        except puente_fusion.ErrorPuenteFusion as e:
            QMessageBox.warning(self, "No se pudo abrir el archivo de Fusion", str(e))
            return
        except (abrir_externo.ErrorAbrir, OSError, ValueError) as e:
            QMessageBox.critical(self, "No se pudo abrir", str(e))
            return
        self.set_documento(doc)
        self._recordar(ruta)
        if avisos:
            QMessageBox.information(self, f"Abierto: {Path(ruta).name}", "\n\n".join(avisos))

    def _esperando(self, texto, funcion):
        """Corre `funcion` en otro hilo mostrando un aviso de espera (la ventana no se congela). Devuelve su
        resultado o relanza su excepción."""
        import threading

        from PySide6.QtCore import QEventLoop
        from PySide6.QtWidgets import QProgressDialog
        resultado = {}

        def trabajo():
            try:
                resultado["valor"] = funcion()
            except Exception as e:  # noqa: BLE001 — se relanza en el hilo de la interfaz
                resultado["error"] = e

        espera = QProgressDialog(texto, None, 0, 0, self)
        espera.setWindowTitle(NOMBRE_APP)
        espera.setWindowModality(Qt.WindowModal)
        espera.setMinimumDuration(300)
        hilo = threading.Thread(target=trabajo, daemon=True)
        hilo.start()
        while hilo.is_alive():           # el hilo de Python no tiene bucle de Qt: se espera atendiendo la interfaz
            QApplication.processEvents(QEventLoop.AllEvents, 50)
            hilo.join(0.05)
        espera.close()
        if "error" in resultado:
            raise resultado["error"]
        return resultado["valor"]

    def _recordar(self, ruta):
        self.prefs.agregar_reciente(str(Path(ruta).resolve()))
        self.panel_datos.recargar()

    def guardar(self):
        if not self._salir_de_boceto():
            return False
        if not self.doc.ruta:
            return self.guardar_como()
        return self._guardar_en(self.doc.ruta)

    def guardar_como(self):
        ruta, _ = QFileDialog.getSaveFileName(self, "Guardar proyecto", f"{self.doc.nombre}.omnicad", FILTRO_PROYECTO)
        return self._guardar_en(ruta) if ruta else False

    def _guardar_en(self, ruta):
        # El documento toma el nombre del archivo ANTES de escribir, para que el manifiesto guarde el mismo nombre.
        nombre_anterior, self.doc.nombre = self.doc.nombre, Path(ruta).stem
        final = None
        try:
            final = proyecto.guardar(self.doc, ruta, self.visor.captura_png())
            proyecto.borrar_autoguardado(self.doc)   # el de la ubicación anterior (o el huérfano "sin título")
            self.doc.ruta = str(final)
            self.doc.modificado = False
            proyecto.borrar_autoguardado(self.doc)   # el de la ubicación nueva, si quedaba uno viejo
            self._actualizar()
            self._recordar(final)
            self.mensaje(f"Guardado en {final}", 5000)
            return True
        except (OSError, RuntimeError) as e:
            if final is None:                         # no llegó a escribir: vuelve el nombre de antes
                self.doc.nombre = nombre_anterior
            QMessageBox.critical(self, "No se pudo guardar", str(e))
            return False

    def autoguardar(self):
        if not self.doc.modificado:
            return
        try:
            destino = proyecto.autoguardar(self.doc)
            self.mensaje(f"Autoguardado {time.strftime('%H:%M')} → {destino.name}", 4000)
        except (OSError, RuntimeError) as e:
            log.warning("Autoguardado falló: %s", e)

    def verificar_autoguardado_huerfano(self):
        pendiente = proyecto.autoguardado_pendiente(None)
        if not pendiente:
            return
        if QMessageBox.question(self, "Recuperar trabajo", "Se encontró un autoguardado de un proyecto sin guardar. "
                                "¿Recuperarlo? (Si respondés No, se descarta.)") != QMessageBox.Yes:
            pendiente.unlink(missing_ok=True)
            return
        try:
            doc = proyecto.abrir(pendiente)
            doc.ruta, doc.nombre, doc.modificado = None, "Recuperado", True
            self.set_documento(doc)
        except (proyecto.ErrorProyecto, OSError, ValueError) as e:
            QMessageBox.critical(self, "No se pudo recuperar", str(e))

    def exportar(self, formato_salida=None):
        cuerpos = list(self.doc.estado_final.cuerpos.values())
        if not cuerpos:
            QMessageBox.information(self, NOMBRE_APP, "No hay cuerpos para exportar.")
            return
        if isinstance(formato_salida, (list, tuple)):
            formatos = list(formato_salida)
        else:
            formatos = [formato_salida] if formato_salida else list(ex.FORMATOS)
        filtros = ";;".join(f"{ex.FORMATOS[f]} (*.{f})" for f in formatos)
        ruta, filtro = QFileDialog.getSaveFileName(self, "Exportar", f"{self.doc.nombre}.{formatos[0]}", filtros)
        if not ruta:
            return
        sufijo = Path(ruta).suffix.lower().lstrip(".")
        if sufijo not in formatos:                    # sin extensión: la del filtro elegido
            sufijo = next((f for f in formatos if f"*.{f}" in filtro), formatos[0])
            ruta = f"{ruta}.{sufijo}"
        try:
            n = ex.exportar(cuerpos, ruta)
            extra = f" ({n} triángulos)" if isinstance(n, int) else ""
            self.mensaje(f"Exportado {len(cuerpos)} cuerpo(s) a {ruta}{extra}", 6000)
        except (ex.ErrorExportacion, RuntimeError, OSError) as e:
            QMessageBox.critical(self, "No se pudo exportar", str(e))

    def capturar_imagen(self):
        ruta, _ = QFileDialog.getSaveFileName(self, "Capturar imagen", f"{self.doc.nombre}.png", "Imagen PNG (*.png)")
        if ruta:
            ok = self.visor.grabFramebuffer().save(ruta, "PNG")
            self.mensaje(f"Imagen guardada en {ruta}" if ok else "No se pudo guardar la imagen", 5000)

    def importar_step(self):
        ruta, _ = QFileDialog.getOpenFileName(self, "Insertar STEP", "", "STEP (*.step *.stp)")
        if not ruta:
            return
        try:
            texto = ex.leer_texto_step(ruta)
        except (ex.ErrorExportacion, RuntimeError, OSError) as e:
            QMessageBox.critical(self, "No se pudo importar", str(e))
            return
        self._agregar(OpImportarSTEP(self.doc.nuevo_id(), f"Importar {Path(ruta).name}", archivo=Path(ruta).name, contenido=texto))

    def insertar_malla(self):
        from ..nucleo import malla
        from ..timeline.ops_malla import OpInsertarMalla
        if not self._salir_de_boceto():
            return
        ruta, _ = QFileDialog.getOpenFileName(self, "Insertar malla", "", "Mallas (*.stl *.obj *.3mf *.ply)")
        if not ruta:
            return
        unidades, ok = QInputDialog.getItem(self, "Insertar malla", "Unidades del archivo:",
                                            ["mm", "cm", "m", "pulgadas", "pies"], 0, False)
        if not ok:
            return
        try:
            m = malla.leer(ruta, unidades=unidades) if not ruta.lower().endswith(".3mf") else malla.leer(ruta)
        except (malla.geo.ErrorGeometria, OSError, ValueError) as e:
            QMessageBox.critical(self, "No se pudo insertar", str(e))
            return
        self._agregar(OpInsertarMalla(self.doc.nuevo_id(), f"Insertar {Path(ruta).name}", archivo=Path(ruta).stem,
                                      datos=m.a_dict()))

    def cargar_ejemplo(self):
        if self._salir_de_boceto() and self._confirmar_descartar():
            self.set_documento(crear_documento_ejemplo())

    def acerca_de(self):
        QMessageBox.about(self, f"Acerca de {NOMBRE_APP}",
                          f"<b>{NOMBRE_APP} {VERSION}</b><br>CAD 3D paramétrico libre, inspirado en el flujo de trabajo "
                          f"de Fusion 360. Los íconos y la interfaz están dibujados desde cero; no usa código ni "
                          f"recursos de otros programas.<br><br>"
                          f"Licencia GNU GPL v3.0 o posterior · "
                          f"<a href='https://github.com/JerryblackVe/OmniCAD'>github.com/JerryblackVe/OmniCAD</a><br>"
                          f"Kernel: OpenCascade (cadquery-ocp) · UI: PySide6 · {self.visor.info_gl}")

    def closeEvent(self, e):
        if self._salir_de_boceto() and self._confirmar_descartar():
            if self.puente is not None:
                self.puente.detener()         # cierra las conexiones y borra puente.json
            e.accept()
        else:
            e.ignore()

