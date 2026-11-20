# -*- coding: utf-8 -*-
"""
Entorno de boceto, como el de Fusion 360 (ver docs/investigacion_boceto_fusion.md).

Se dibuja DIRECTAMENTE sobre el plano, en la vista 3D: el Lienzo es una capa transparente encima
del visor que proyecta el boceto con la cámara del visor, así que se puede orbitar, desplazar y
hacer zoom mientras se dibuja (botón del medio, Mayús + medio, rueda; el izquierdo dibuja).
Sin visor, el Lienzo trabaja en 2D (lo usan las pruebas).

Comportamiento tomado de la ayuda de Fusion (libro "Design: Sketch", SKT-*):
  - Línea: clic, clic… encadena segmentos; arrastrar desde el último punto crea un arco tangente;
    escribir un número abre la entrada de longitud (Tab pasa al ángulo) y crea la cota; Esc corta.
  - CREAR: rectángulos, círculos (centro, 2 y 3 puntos, 2 y 3 tangentes), arcos, polígonos, elipse,
    ranuras (5 tipos), splines de ajuste y de puntos de control, cónica, punto, texto, espiral,
    simetría, patrones rectangular y circular, Proyectar / Intersecar / Incluir geometría 3D.
  - MODIFICAR: empalme, chaflanes, curva de fusión (G1/G2), desfase (O), recortar (T), alargar,
    partir, escala, mover/copiar (M).
  - Al enganchar un punto existente se comparte (coincidencia) y, si un segmento queda casi a 0° o
    90°, se agrega horizontal o vertical automáticamente (restricciones inferidas).
  - Cota de boceto (D): clic en la geometría, clic para ubicar, se escribe el valor o una expresión
    con parámetros y Enter. Doble clic en una cota la edita (y en un texto, edita el texto); el clic
    derecho suma «Editar valor» y «Renombrar parámetro», y al pasar el mouse muestra «nombre : valor».
  - Restricciones: se elige la herramienta y se hace clic en la geometría (o se preselecciona).
  - Herramientas que trabajan sobre una selección (simetría, patrones, escala, mover): se usa lo
    preseleccionado o se eligen las curvas con clics y Enter para seguir.
  - Colores: azul = libre, blanco/negro = totalmente restringido, verde = fijo, naranja punteado =
    construcción, violeta = proyectada; los ejes (líneas centrales) van con trazo y punto. X alterna
    normal/construcción. Supr borra. Ctrl+Z deshace dentro del boceto.
"""

from .editor_boceto_comun import (
    copy as copy,
    math as math,
    re as re,
    threading as threading,
    time as time,
    warnings as warnings,
    replace as replace,
    np as np,
    QEvent as QEvent,
    QEventLoop as QEventLoop,
    QPoint as QPoint,
    QPointF as QPointF,
    QRectF as QRectF,
    Qt as Qt,
    QTimer as QTimer,
    Signal as Signal,
    QColor as QColor,
    QFontMetricsF as QFontMetricsF,
    QKeySequence as QKeySequence,
    QMouseEvent as QMouseEvent,
    QPainter as QPainter,
    QPen as QPen,
    QPixmap as QPixmap,
    QPolygonF as QPolygonF,
    QApplication as QApplication,
    QDialog as QDialog,
    QFrame as QFrame,
    QHBoxLayout as QHBoxLayout,
    QInputDialog as QInputDialog,
    QLabel as QLabel,
    QLineEdit as QLineEdit,
    QMenu as QMenu,
    QToolButton as QToolButton,
    QToolTip as QToolTip,
    QWidget as QWidget,
    fuentes as fuentes,
    Boceto as Boceto,
    ErrorBoceto as ErrorBoceto,
    TIPOS_COTA as TIPOS_COTA,
    TIPOS_RESTRICCION as TIPOS_RESTRICCION,
    auto_restringir as auto_restringir,
    grados_de_libertad as grados_de_libertad,
    resolver as resolver,
    acomodar_tangente as acomodar_tangente,
    restricciones_en_conflicto as restricciones_en_conflicto,
    restricciones_redundantes as restricciones_redundantes,
    restriccion_quita_grados as restriccion_quita_grados,
    Indice as Indice,
    TIPOS_INFERENCIA as TIPOS_INFERENCIA,
    inferencias as inferencias,
    proyectar_bloqueo as proyectar_bloqueo,
    Arco as Arco,
    Circulo as Circulo,
    Conica as Conica,
    Cota as Cota,
    Linea as Linea,
    Spline as Spline,
    Texto as Texto,
    agregar_linea_medio as agregar_linea_medio,
    agregar_rectangulo_3p as agregar_rectangulo_3p,
    aviso_radio_empalme as aviso_radio_empalme,
    aviso_tangencias_fuera as aviso_tangencias_fuera,
    agregar_arco_tangente as agregar_arco_tangente,
    agregar_circulo_puntos as agregar_circulo_puntos,
    agregar_estrella as agregar_estrella,
    agregar_poligono as agregar_poligono,
    agregar_rectangulo_centro as agregar_rectangulo_centro,
    cambiar_radio as cambiar_radio,
    centro_arco_tangente as centro_arco_tangente,
    centro_poligono_arista as centro_poligono_arista,
    circunferencia_3_puntos as circunferencia_3_puntos,
    dominio as dominio,
    evaluar_primitiva as evaluar_primitiva,
    expresion_sin_signo as expresion_sin_signo,
    fraccion_en_camino as fraccion_en_camino,
    lado_natural as lado_natural,
    mas_cercano as mas_cercano,
    paradas_cursor as paradas_cursor,
    primitivas_entidad as primitivas_entidad,
    proporcion_estrella as proporcion_estrella,
    puntos_espiral as puntos_espiral,
    puntos_primitiva as puntos_primitiva,
    redondear_estrella as redondear_estrella,
    redondeos_estrella as redondeos_estrella,
    validar_lados_poligono as validar_lados_poligono,
    validar_puntas_estrella as validar_puntas_estrella,
    validar_valor_cota as validar_valor_cota,
    vertices_estrella as vertices_estrella,
    vertices_poligono as vertices_poligono,
    _validar_opciones_texto as _validar_opciones_texto,
    ANGULO as ANGULO,
    ESCALAR as ESCALAR,
    LONGITUD as LONGITUD,
    ErrorExpresion as ErrorExpresion,
    nombres_usados as nombres_usados,
    separar_nombre as separar_nombre,
    validar_nombre as validar_nombre,
    _ru as _ru,
    formato as formato,
    temas as temas,
    autocompletar as autocompletar,
    icono as icono,
    ControlPatron as ControlPatron,
    dibujar_casilla as dibujar_casilla,
    ControlTransformar as ControlTransformar,
    HERRAMIENTAS as HERRAMIENTAS,
    RESTRICCIONES_HERRAMIENTA as RESTRICCIONES_HERRAMIENTA,
    NOMBRES_RESTRICCION as NOMBRES_RESTRICCION,
    AYUDA_RESTRICCION as AYUDA_RESTRICCION,
    DETALLE_RESTRICCION as DETALLE_RESTRICCION,
    ICONO_RESTRICCION as ICONO_RESTRICCION,
    LADO_SIMBOLO as LADO_SIMBOLO,
    RELACION_ENTRE_DOS as RELACION_ENTRE_DOS,
    NOMBRES_ENTIDAD as NOMBRES_ENTIDAD,
    PICKS as PICKS,
    SELECCION as SELECCION,
    PATRON as PATRON,
    TRANSFORMAR as TRANSFORMAR,
    SPLINES as SPLINES,
    PROYECCION as PROYECCION,
    COMANDO_PROYECCION as COMANDO_PROYECCION,
    CAPA_PROYECCION as CAPA_PROYECCION,
    CURVA_TEXTO as CURVA_TEXTO,
    MODIFICAN as MODIFICAN,
    PORTAPAPELES as PORTAPAPELES,
    VIOLETA as VIOLETA,
    TOL_PX as TOL_PX,
    TOL_PUNTO as TOL_PUNTO,
    TOL_MANIJA as TOL_MANIJA,
    RADIO_INTERIOR_PX as RADIO_INTERIOR_PX,
    TOL_INFERENCIA as TOL_INFERENCIA,
    EJES_ORIGEN as EJES_ORIGEN,
    AJUSTES_INFERENCIA as AJUSTES_INFERENCIA,
    ajustes_inferencia as ajustes_inferencia,
    RANURAS_RECTAS as RANURAS_RECTAS,
    VIVAS as VIVAS,
    ANGULARES as ANGULARES,
    COTA_OSCURO as COTA_OSCURO,
    COTA_CLARO as COTA_CLARO,
    REFERENCIA as REFERENCIA,
    AZUL_CAJA as AZUL_CAJA,
    FONDO_LIENZO as FONDO_LIENZO,
    CAPA_PREVIA_ISO as CAPA_PREVIA_ISO,
    COLOR_PREVIA_ISO as COLOR_PREVIA_ISO,
    TOPE_DIAGNOSTICO_S as TOPE_DIAGNOSTICO_S,
    CONFLICTO as CONFLICTO,
    VENTANA_RELLENO as VENTANA_RELLENO,
    VENTANA_BORDE as VENTANA_BORDE,
    VENTANA_CRUCE as VENTANA_CRUCE,
    AVISO_BORRADAS as AVISO_BORRADAS,
    YA_PROYECTADA as YA_PROYECTADA,
    _cantidad as _cantidad,
    texto_proyeccion as texto_proyeccion,
    _tipo_valor as _tipo_valor,
    _unitario as _unitario,
    _distancia_a_raya as _distancia_a_raya,
    _rotar as _rotar,
    _tenido as _tenido,
    _es_numero as _es_numero,
    texto_valor as texto_valor,
    _vertices_poligono as _vertices_poligono,
    _segmento_en_rect as _segmento_en_rect,
    CampoVivo as CampoVivo,
    _dist_px as _dist_px,
    _barrido as _barrido,
    _numero as _numero,
    _espaciado_cien as _espaciado_cien,
    _espaciado_mm as _espaciado_mm,
    _espaciado_porcentaje as _espaciado_porcentaje,
    _CACHE_MUESTRAS as _CACHE_MUESTRAS,
    _muestras as _muestras,
    _inicio_palabra as _inicio_palabra,
    _fin_palabra as _fin_palabra,
    _palabra_en as _palabra_en,
    PEDIR_DISTANCIA as PEDIR_DISTANCIA,
    PISTA_DESFASE as PISTA_DESFASE,
    EntradaValor as EntradaValor,
    _registro_uso as _registro_uso,
    _diff_uso as _diff_uso,
    _foto_uso as _foto_uso,
    _suelta_aislada as _suelta_aislada,
)
from .editor_boceto_base import LienzoBaseMixin as _LienzoBaseMixin
from .editor_boceto_crear import LienzoCrearMixin as _LienzoCrearMixin
from .editor_boceto_modificar import LienzoModificarMixin as _LienzoModificarMixin
from .editor_boceto_proyeccion import LienzoProyeccionMixin as _LienzoProyeccionMixin
from .editor_boceto_texto import LienzoTextoMixin as _LienzoTextoMixin
from .editor_boceto_cotas import LienzoCotasMixin as _LienzoCotasMixin
from .editor_boceto_restricciones import LienzoRestriccionesMixin as _LienzoRestriccionesMixin
from .editor_boceto_interaccion import LienzoInteraccionMixin as _LienzoInteraccionMixin
from .editor_boceto_dibujo import LienzoDibujoMixin as _LienzoDibujoMixin


class Lienzo(_LienzoBaseMixin,
        _LienzoCrearMixin,
        _LienzoModificarMixin,
        _LienzoProyeccionMixin,
        _LienzoTextoMixin,
        _LienzoCotasMixin,
        _LienzoRestriccionesMixin,
        _LienzoInteraccionMixin,
        _LienzoDibujoMixin,
        QWidget):
    cambio = Signal()
    mensaje = Signal(str)
    herramienta_cambiada = Signal(str)
    texto_en_edicion = Signal()     # se abre el cuadro de un texto (nuevo o ya creado): la paleta muestra sus opciones
    texto_valores = Signal(float, float, float, float, bool)   # altura, interletraje, interlineado, kerning en el cursor y si hay par
    info = Signal(str)          # medidas de lo elegido, como Fusion ("1 línea de boceto | Longitud: …")
    seleccion_cambiada = Signal()   # la ventana la refleja en el navegador
    aviso = Signal(str)         # aviso flotante (p. ej. una operación borró restricciones o cotas)
    simetria_estado = Signal(object)    # lo que muestra el panel SIMETRÍA (ver `estado_simetria`)
    proyeccion_estado = Signal(object)  # lo que muestra la tarjeta de Proyectar (ver `estado_proyeccion`)

    def __init__(self, boceto, evaluar, parent=None, visor=None, plano=None):
        super().__init__(parent)
        self.b = boceto
        self._evaluar_doc = evaluar
        self._nombradas = {}             # nombre dN → id de las cotas que se nombraron al citarlas (BOC-35)
        self.visor, self.plano = visor, plano
        self.herramienta = "seleccionar"
        self.ultima_herramienta = None
        self.construccion = False
        self.eje = False                           # tipo de línea "línea central" para lo nuevo
        self.ajustar_grilla = visor is None          # en la vista 3D, "Forzar" arranca apagado (Fusion)
        self.mostrar = {"puntos": True, "cotas": True, "restricciones": True, "construccion": True, "rejilla": True,
                        "proyectadas": True}
        self.opcion_cota = "auto"
        self.lados = 6
        self._ultima_figura = None       # P-154: el polígono o la estrella recién dibujados (Lados los rehace)
        # Opciones de la paleta (Opciones de función de Fusion) para las herramientas nuevas.
        self.opciones = {"grado_spline": 5, "continuidad": "G1", "puntas_estrella": 5, "interior_estrella": 0.0,
                         "salto_estrella": 2, "circulos_estrella": True,
                         "redondeo_puntas": 0.0, "redondeo_valles": 0.0,
                         "filtro_proyectar": "entidades", "copiar": False, "fuente": "Arial",
                         "direccion_desfase": "un", "match_topology": False, "seleccion_cadena": True,
                         "vinculo_proyeccion": True, "eje_giro": "Z", "contorno_exterior": True, "proyectar_eje": False,
                         "tolerancia_giro": 0.1, "invertir_giro": False,
                         "iso_direccion": "u", "iso_tipo": "unica", "iso_distancia": 10.0, "iso_cantidad": 5,
                         "pivote_texto": None, "marco_texto": False, "marco_fijo": False, "parametro_texto": None,
                         "valor_parametro_texto": "",
                         "negrita": False, "cursiva": False,
                         "alineacion": "izq", "ancla_v": "base", "camino_lado": "izq", "camino_colocacion": "arriba",
                         "camino_desfase": 0.0, "camino_ajustar": False,
                         "altura_texto": 5.0, "espaciado": 0.0, "interlineado": 1.0,
                         "voltear_h": False, "voltear_v": False,
                         **{k: Texto._PREDETERMINADOS[k] for k in Texto.TIPOGRAFIA}}
        self.perdidas = []                         # ids de proyecciones perdidas en el último cálculo (los pone el modo)
        self._revincular = None                    # proyección perdida que se re-vincula con el próximo clic
        self._brillantes = None                    # ids que se ven normales con «Atenuar el resto» (None: todo normal)
        self._eje_giro = None                      # (eje, referencia) de la arista elegida para el perfil giratorio
        self._elegidos_proy = []                   # lo elegido en la tarjeta de Proyectar / Intersecar (sin aceptar)
        self._nota_proy = ""                       # aviso de la tarjeta (p. ej. lo que sacó un cambio de filtro)
        self._previa_proy = {"prims": [], "puntos": []}      # lo que se dibuja como resultado provisional
        self.op_boceto = None                      # paso del timeline de este boceto (None: todavía no tiene)
        self.estado_referencias = lambda: None     # el modo consulta el estado actual del documento
        self._sel_texto = []                       # cuadriláteros de lo seleccionado en el texto que se escribe
        self._arrastre_texto = False               # se está seleccionando texto arrastrando el ratón
        self._paleta_texto = False                 # la paleta muestra las opciones del texto que se edita
        self._previa_texto = None                  # texto en vivo mientras se escribe en la caja (como Fusion)
        self._previa_polis = []                    # contornos de esa vista previa (coordenadas del boceto)
        self._texto_oculto = None                  # texto existente en edición: en su lugar se dibuja la previa
        self.editar_parametro_texto = None         # el modo usa set_parameter sobre el documento
        self.valores_parametros = lambda: {}
        self._caret = None                         # segmento del cursor de escritura, en coordenadas del boceto
        self._caret_on = True
        self._t_caret = QTimer(self)
        self._t_caret.setInterval(530)
        self._t_caret.timeout.connect(self._parpadeo)
        self.escala = 4.0
        self.centro = [0.0, 0.0]
        self.seleccion = []
        self.mostrar_marco = True       # marco de control (Fusion: «Mostrar el marco de control») sobre lo elegido
        self._marco = None              # arrastre en curso de una manija del marco
        self.clics = []
        self.picks = []
        self.picks_xy = []
        self.fase = None             # en herramientas de varios pasos: seleccion | eje | base | destino | centro
        self._eje_simetria = None        # SIMETRÍA: la línea de simetría elegida (el panel Eje de simetría)
        self.previa_simetria = True      # SIMETRÍA: la casilla «Vista previa» del panel
        self._error_simetria = ""        # SIMETRÍA: último reparo del panel (se borra al cambiar lo elegido)
        self._previa_sim = None          # SIMETRÍA: (clave, polilíneas, error) de la copia reflejada, con caché
        self._firma_sim = self._estado_sim = None   # SIMETRÍA: lo elegido y lo último que se le mandó al panel
        self.cursor = None
        self.inferencia = None
        self.inf_actual = None
        self.inf_lista = []              # todas las ayudas bajo el cursor, la activa primero (Espacio alterna)
        self.ayuda_3d = None             # (posición en px, tipo, etiqueta) de la ayuda del Boceto 3D (`ui/triada3d.py`)
        self.ajustes_inf = dict(AJUSTES_INFERENCIA)
        self._indice_inf = None          # geometría derivada para consultar rápido; se descarta al cambiar el boceto
        self._indice_clave = None
        self._puntos_np = None           # (clave, ids, coordenadas) de todos los puntos, para capturarlos en bloque
        self._cache_splines = {}         # id → (lo que define la spline de ajuste, sus primitivas): ver `_polilineas`
        self._capa_clave = self._capa_img = None    # imagen de las curvas y lo que dibuja: ver `_dibujar_capa_curvas`
        self._inf_alt = 0
        self._inf_claves = []            # qué ayudas había en el movimiento anterior: si cambian, Espacio vuelve a la primera
        self._inf_bloqueo = None         # ayuda bloqueada con Flecha arriba: el cursor sigue su guía
        self._inf_bloqueo_clics = 0      # pulsaciones que había al bloquear: otra pulsación la suelta
        self._inf_inicio = None
        self._inf_lado = None
        self._inf_radio = None           # BOC-33: la ayuda del clic de radio del arco con centro, hasta el clic final
        self._inf_clics = []          # BOC-9: (xy, tipo, objetivo) de cada clic, para las herramientas que no son Línea
        self._eligiendo_punto = None     # BOC-5: {"lazo", "pid"} mientras se elige el datum en el lienzo
        self.perfiles_sel = []           # BOC-23: índices de los perfiles elegidos con un clic (orden de `detectar`)
        self._modificadores_raton = Qt.NoModifier
        self.historial = []
        self.pila_rehacer = []
        self.resultado = None
        self._conflictos = []            # BOC-7: ids de restricciones/cotas en choque (se pintan en rojo)
        self._generacion = 0             # B-111: cuenta los cambios del boceto; un diagnóstico de otra generación se descarta
        self._diagnostico_agotado = False   # el diagnóstico pasó TOPE_DIAGNOSTICO_S sin terminar
        self._diagnostico = None         # (generación, caja) del diagnóstico de conflictos que corre en otro hilo
        self._mostrar_conflictos_al_llegar = False
        self._t_diagnostico = QTimer(self)
        self._t_diagnostico.setSingleShot(True)
        self._t_diagnostico.timeout.connect(self._sondear_conflictos)
        self.previa_auto = []
        self.entrada = None
        self._proy_fusion = 0                      # B-256: aristas proyectadas por la Curva de fusión en curso
        self._asas = None                          # asas de arrastre de la herramienta (ui/asas_boceto.py)
        self.patron = ControlPatron(self)          # Patrón rectangular y circular: estado, vista previa y panel
        self.transformar = ControlTransformar(self)    # Escala y Mover/copiar: estado, vista previa y panel
        self._desfase_invertido = False            # botón «Invertir» de la barra del Desfase
        self._desfase_modo = "un"                   # dirección con la que se abrió esa barra
        self._desfase_conservar = None              # (textos, invertido) que pasan a la curva elegida en su lugar
        self.copias_en_edicion = frozenset()        # BOC-60: copias del patrón que se edita: no se dibujan ni se agarran
        self._desfase_perfil = None                 # BOC-70: ids del borde del perfil elegido con un clic adentro, o None
        self._desfase_elipse = False                # BOC-71: la elipse se eligió cerca de un eje: da otra elipse, no un óvalo
        self._previa_desfase_cache = None           # (clave, resultado) de la última vista previa del Desfase
        self._mvp = None
        self._sobre = None               # entidad bajo el ratón en Seleccionar (se resalta y cambia el cursor)
        self._manija_sobre = None        # manija del marco bajo el ratón
        self._zona_sobre = None          # cota o símbolo de restricción bajo el ratón
        self._arrastre, self._movio = None, False
        self._desliz = None              # (fracción al agarrar, posición del texto, camino cerrado)
        self._presion = None
        self._tangente = None            # (punto de partida, línea) mientras se arrastra un arco tangente
        self._ventana = None
        self._pan = None
        self._reenvio = None
        self._ultima_linea = None
        self._zonas_cotas, self._zonas_glifos, self._trazos_cotas = {}, {}, {}
        self._zonas_glifos_extra = []     # [(id, caja)]: el símbolo de la 2.ª entidad de una relación (el 1.º va en _zonas_glifos)
        self._fondos_cotas = {}          # cota → caja del fondo de su texto (para las pruebas y el repintado)
        self._esperando_ubicacion = False
        self._pos_cursor = QPointF(0, 0)
        self._presion_inferencia = None
        self._presion_inf_actual = None
        self._cache_cortes = {}
        self._previa_recorte = None
        self._recorte_arrastre = None    # None: sin gesto; False: presionado; True: ya recortó
        # Cotas en vivo: lo escrito queda bloqueado (clave → (texto, valor)) hasta crear la geometría.
        self._bloqueos = {}
        self._activo = 0                 # caja activa (Tab pasa a la siguiente)
        self._editando = None            # clave de la caja que se está escribiendo
        self._post_crear = None          # agrega las cotas de lo escrito dentro del mismo paso de deshacer
        self._sentido_vivo = None        # arco de punto central con el barrido escrito: antihorario o no
        self._cajas_vivas = []           # [(clave, QRectF)] dibujadas
        self._ultimo = None              # arrastre de curvas: última posición del ratón (mm)
        self._info = None                # último texto de medidas emitido
        self._cota_editada = None
        self._cota_previa = None         # Cota provisional (id -1) mientras se escribe su valor
        self._cota_abierta = None        # (tipo, entidades, pos) de la cota nueva cuya caja está abierta
        self._opc_cota = {}              # opciones del menú antes de ubicar: referencia, tipo, modo (BOC-34)
        self._evaluando = set()          # nombres en evaluación: corta las referencias circulares
        self._cita_sobre = None          # cota bajo el ratón: se cita con una caja abierta o muestra su cartel
        self._texto_inicial = None       # valor con el que se abrió la caja de valor
        self._derecho = None             # (pos px, pos global) del clic derecho apretado en una herramienta
        self._t_derecho = QTimer(self)   # clic derecho mantenido con una cota a medias: menú de opciones (BOC-34)
        self._t_derecho.setSingleShot(True)
        self._t_derecho.timeout.connect(self._opciones_cota_mantenido)
        self._iso_pos = self._iso_texto = None   # isoparamétrica: cursor y último aviso de la vista previa (BOC-75)
        self._iso_dibujada = False
        self._t_iso = QTimer(self)              # la vista previa se arma con el cursor quieto, no en cada movimiento
        self._t_iso.setSingleShot(True)
        self._t_iso.timeout.connect(self._previa_iso)
        self.setMouseTracking(True)
        self.setFocusPolicy(Qt.StrongFocus)
        if visor is None:
            self.setMinimumSize(520, 420)
        else:
            self.setAttribute(Qt.WA_TranslucentBackground)
            visor.camara_cambiada.connect(self.update)
        from .objetos_vectoriales import ControlObjetos
        self.objetos = ControlObjetos(self)
        self.resolver()

    @property
    def conflictos(self):
        """BOC-7: ids de restricciones/cotas cuya retirada sola resuelve el conflicto (vacía si no hay conflicto).
        Espera el cálculo (lo usan los tests y la API); el pintado y los textos usan `conflictos_sin_esperar`.
        shortcut: una resolución por vínculo; se calcula una vez por estado y solo si hay conflicto."""
        if self._conflictos is None:
            self._conflictos = restricciones_en_conflicto(self.b, self._valores_para_diagnostico())
        return self._conflictos

    def conflictos_sin_esperar(self):
        """B-111: lo que ya se sabe del diagnóstico ([] mientras se calcula, que corre en otro hilo con «lo último
        gana»). Al llegar se emite `cambio` y se repinta, así que el rojo y el texto aparecen un poco después."""
        if self._conflictos is None:
            if self._diagnostico is None:
                caja, generacion = {}, self._generacion
                copia, valores = self.b.copia(), self._valores_para_diagnostico()

                def correr():
                    try:
                        limite = time.monotonic() + TOPE_DIAGNOSTICO_S
                        caja["res"] = restricciones_en_conflicto(
                            copia, valores, lambda: generacion != self._generacion or time.monotonic() > limite)
                    except Exception as e:  # noqa: BLE001 — se vuelve a lanzar en el hilo de la ventana
                        caja["error"] = e
                    caja["listo"] = True
                self._diagnostico = (generacion, caja)
                threading.Thread(target=correr, daemon=True).start()
                self._t_diagnostico.start(40)
            return []
        return self._conflictos
