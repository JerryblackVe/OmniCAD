# -*- coding: utf-8 -*-
"""
Piezas comunes de los formularios de herramientas: lo que comparten los paneles de comando (`ui/comando.py`) y los
paneles de boceto (patrón, simetría…). Sin lógica geométrica: solo cómo se presentan las cosas.

  - `ANCHOS`: ancho fijo del panel según su complejidad (no depende de la etiqueta más larga ni cambia al teclear).
  - `describir_ref` / `describir_seleccion`: qué se ve en una fila de selección («Cara plana +Z · Caja1», «3 aristas · Caja1»)
    sin tocar la referencia geométrica que se guarda.
  - `Seccion`: grupo plegable de opciones poco frecuentes, con resumen de lo que hay activo cuando está cerrada.
  - `TIPOS_MENSAJE`: los cinco estados que muestra el pie (instrucción, inválido, advertencia, calculando, error).
  - `armar_cabecera` / `fila_mensaje` / `poner_mensaje` / `armar_estado`: la cabecera movible (ícono, título, botones y ✕) y la línea de
    estado con símbolo que usan TODOS los paneles de herramienta (comando, patrón, simetría, escala/mover y carácter).
"""
from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import QGridLayout, QHBoxLayout, QLabel, QSizePolicy, QToolButton, QVBoxLayout, QWidget

from . import temas
from .superposiciones import CabeceraMovible

# Ancho del panel (px) por complejidad: formulario corto, normal (la mayoría) y con tablas o filas anchas.
ANCHOS = {"simple": 320, "normal": 360, "ancho": 460}
# Etiqueta y columna de los campos: iguales en todos los paneles para que las filas se alineen entre herramientas.
ANCHO_ETIQUETA = 124

# tipo de mensaje → (símbolo, color del tema). El símbolo acompaña al color: no se depende solo de él.
TIPOS_MENSAJE = {"instruccion": ("➜", "enlace"), "invalido": ("✖", "error"), "aviso": ("⚠", "aviso"),
                 "calculando": ("⏳", "texto_tenue"), "error": ("✖", "error")}

_GEOM_CARA = {"plano": "plana", "cilindro": "cilíndrica", "cono": "cónica", "esfera": "esférica", "toro": "toroidal",
              "otra": "libre"}
_GEOM_ARISTA = {"linea": "recta", "circulo": "circular", "elipse": "elíptica", "otra": "curva"}
_PLURAL = {"cara": "caras", "arista": "aristas", "vertice": "vértices", "cuerpo": "cuerpos", "perfil": "perfiles",
           "curva_boceto": "curvas de boceto", "punto_boceto": "puntos de boceto", "plano": "planos", "eje": "ejes",
           "punto": "puntos", "boceto": "bocetos", "forzado": "puntos de forzado"}
_SINGULAR = {"cara": "cara", "arista": "arista", "vertice": "vértice", "cuerpo": "cuerpo", "perfil": "perfil",
             "curva_boceto": "curva de boceto", "punto_boceto": "punto de boceto", "plano": "plano", "eje": "eje",
             "punto": "punto", "boceto": "boceto", "forzado": "punto de forzado"}
_FORZADOS = {"centro_cara": "Centro", "tangencial": "Punto tangencial", "lugar_cara": "Punto", "centro_arista": "Centro",
             "en_arista": "Punto", "lugar_plano": "Punto"}


def _nombre_op(ctx, op_id):
    """Nombre del paso del timeline con ese id (un plano, eje o boceto de construcción); el id si no está."""
    op = next((o for o in ctx.doc.operaciones if o.id == op_id), None)
    return op.nombre if op is not None else str(op_id)


def _nombre_cuerpo(ctx, cid):
    c = ctx.estado.cuerpos.get(cid)
    return c.nombre if c is not None else f"{cid} (ya no existe)"


def _eje_cartesiano(v):
    """«+Z», «-X»… si el vector apunta a un eje; "" si está inclinado."""
    for i, nombre in enumerate("XYZ"):
        if abs(abs(v[i]) - 1) < 1e-6 and all(abs(v[j]) < 1e-6 for j in range(3) if j != i):
            return ("+" if v[i] > 0 else "-") + nombre
    return ""


def describir_ref(ref, ctx):
    """Texto corto y legible de una referencia: tipo, rasgo que la distingue y a qué pertenece."""
    t = ref.get("tipo")
    if t == "cuerpo":
        return _nombre_cuerpo(ctx, ref.get("cuerpo"))
    if t in ("cara", "arista", "vertice"):
        firma, cuerpo = ref.get("firma") or {}, _nombre_cuerpo(ctx, ref.get("cuerpo"))
        geom = firma.get("geom")
        if t == "cara":
            rasgo = _GEOM_CARA.get(geom, "")
            extra = _eje_cartesiano(firma["normal"]) if geom == "plano" and "normal" in firma else \
                (f"Ø{2 * firma['radio']:.4g}" if "radio" in firma else "")
            return f"Cara {rasgo} {extra}".replace("  ", " ").strip() + f" · {cuerpo}"
        if t == "arista":
            medida = f"Ø{2 * firma['radio']:.4g}" if geom == "circulo" and "radio" in firma else \
                (f"{firma['largo']:.4g} mm" if "largo" in firma else "")
            return f"Arista {_GEOM_ARISTA.get(geom, '')} {medida}".replace("  ", " ").strip() + f" · {cuerpo}"
        return f"Vértice · {cuerpo}"
    if t == "plano":
        i = ref.get("id")
        return f"Plano {i}" if i in ("XY", "XZ", "YZ") else f"Plano {_nombre_op(ctx, i)}"
    if t == "eje":
        i = ref.get("id")
        return f"Eje {i}" if i in ("X", "Y", "Z") else f"Eje {_nombre_op(ctx, i)}"
    if t == "punto":
        i = ref.get("id")
        return "Origen" if i == "O" else f"Punto {_nombre_op(ctx, i)}"
    if t == "perfil":
        return f"Perfil · {_nombre_op(ctx, ref.get('boceto'))}"
    if t == "curva_boceto":
        return f"Curva {ref.get('curva')} · {_nombre_op(ctx, ref.get('boceto'))}"
    if t == "punto_boceto":
        return f"Punto {ref.get('punto')} · {_nombre_op(ctx, ref.get('boceto'))}"
    if t == "boceto":
        return f"Boceto {_nombre_op(ctx, ref.get('boceto'))}"
    if t == "forzado":
        return f"{_FORZADOS.get(ref.get('modo'), 'Punto')} de {describir_ref(ref.get('base') or {}, ctx)}"
    if t == "componente":
        return str(ctx.estado.componentes.get(ref.get("componente"), {}).get("nombre", ref.get("componente")))
    if t == "centro_masa":
        return str(ref.get("analisis"))
    return str(t or "?")


def _origen(hit):
    """Marca de cómo entró la referencia: elegida a mano (nada), preseleccionada antes del comando o automática."""
    return {"previa": " · preelegida", "auto": " · automática"}.get(hit.get("origen"), "")


def describir_seleccion(hits, ctx):
    """(texto del botón, detalle para el tooltip) de lo elegido en un campo. Vacío = ("", "")."""
    if not hits:
        return "", ""
    lineas = [describir_ref(h["ref"], ctx) + _origen(h) for h in hits]
    if len(hits) == 1:
        return lineas[0], lineas[0]
    tipos = {h["ref"].get("tipo") for h in hits}
    cuerpos = {h["ref"].get("cuerpo") for h in hits if h["ref"].get("cuerpo")}
    nombre = _PLURAL.get(tipos.pop(), "objetos") if len(tipos) == 1 else "objetos"
    de = f" · {_nombre_cuerpo(ctx, next(iter(cuerpos)))}" if len(cuerpos) == 1 else ""
    return f"{len(hits)} {nombre}{de}", "\n".join(lineas)


_NOMBRE_FILTRO = {"cara_plana": "cara plana", "arista_lineal": "arista recta", "arista_circular": "arista circular",
                  "curva_boceto": "curva", "punto_boceto": "punto de boceto"}


def texto_filtros(filtros, varios=False):
    """«Elegir perfil o cara plana»: lo que el campo espera, para la fila vacía (el filtro del visor ya impide elegir otra
    cosa). Si hay un tipo general (cara) no se repite su variante (cara plana). `varios` no cambia el texto: lo dice el tooltip."""
    orden = ("perfil", "cara", "cara_plana", "arista", "arista_lineal", "arista_circular", "vertice", "cuerpo",
             "curva_boceto", "punto_boceto", "boceto", "plano", "eje", "punto")
    general = {"cara_plana": "cara", "arista_lineal": "arista", "arista_circular": "arista"}
    nombres = []
    for f in sorted(filtros, key=lambda f: orden.index(f) if f in orden else 99):
        if general.get(f) in filtros:
            continue
        n = _NOMBRE_FILTRO.get(f) or _SINGULAR.get(f, f)
        if n not in nombres:
            nombres.append(n)
    texto = ", ".join(nombres[:-1]) + " o " + nombres[-1] if len(nombres) > 1 else (nombres[0] if nombres else "objeto")
    return f"Elegir {texto}"


def nombre_tipo(hit):
    """«cara», «arista»… de una selección (para mensajes)."""
    return _SINGULAR.get(hit["ref"].get("tipo"), "objeto")


class Seccion(QWidget):
    """Grupo plegable («Más opciones»): cerrado muestra una línea de resumen con lo que está activo dentro, para que una
    opción importante nunca quede escondida sin aviso. Plegar o desplegar no recalcula nada (solo cambia lo que se ve)."""
    plegada = Signal(bool)

    def __init__(self, titulo, abierta=False, parent=None):
        super().__init__(parent)
        self.titulo = titulo
        v = QVBoxLayout(self)
        v.setContentsMargins(0, 2, 0, 0)
        v.setSpacing(2)
        self.boton = QToolButton(objectName="seccion_cmd", checkable=True, checked=abierta, text=titulo,
                                 toolButtonStyle=Qt.ToolButtonTextBesideIcon, arrowType=Qt.DownArrow if abierta else Qt.RightArrow)
        self.boton.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Fixed)        # el título no ensancha el panel
        self.boton.setToolTip("Mostrar u ocultar estas opciones")
        self.boton.toggled.connect(self._alternar)
        v.addWidget(self.boton)
        self.resumen = QLabel(objectName="resumen_seccion", wordWrap=True)
        self.resumen.hide()
        v.addWidget(self.resumen)
        self.cuerpo = QWidget()
        self.grilla = QGridLayout(self.cuerpo)
        self.grilla.setContentsMargins(0, 2, 0, 0)
        self.grilla.setHorizontalSpacing(10)
        self.grilla.setVerticalSpacing(5)
        self.grilla.setColumnMinimumWidth(0, ANCHO_ETIQUETA)
        self.grilla.setColumnStretch(1, 1)
        v.addWidget(self.cuerpo)
        self.cuerpo.setVisible(abierta)      # con padre: suelto se mostraría como ventana (B-136)
        self._texto_resumen = ""

    @property
    def abierta(self):
        return self.boton.isChecked()

    def _alternar(self, abierta):
        self.boton.setArrowType(Qt.DownArrow if abierta else Qt.RightArrow)
        self.cuerpo.setVisible(abierta)
        self.set_resumen(self._texto_resumen)
        self.plegada.emit(abierta)

    def set_resumen(self, texto):
        """Línea que se ve con la sección cerrada ("" = nada activo): qué opciones tiene en uso."""
        self._texto_resumen = texto
        self.resumen.setText(texto)
        self.resumen.setVisible(not self.abierta and bool(texto))
        self.boton.setText(f"{self.titulo} ●" if texto and not self.abierta else self.titulo)


def armar_cabecera(tarjeta, cancelar, extras=(), tooltip_cerrar="Cancelar (Esc)"):
    """Cabecera movible de un panel de herramienta: ícono, título (el que ajusta el panel), los botones `extras` y ✕
    (Cancelar, Esc; sin `cancelar` no hay ✕). Arrastrarla mueve el panel (`tarjeta.posicion_usuario`); el doble clic lo devuelve a su lugar.
    Devuelve (cabecera, ícono, título). ✕ no toma el foco: Tab empieza en los campos y Esc ya cancela."""
    tarjeta.posicion_usuario = None
    cab = CabeceraMovible(tarjeta)
    h = QHBoxLayout(cab)
    h.setContentsMargins(8, 4, 4, 4)
    icono = QLabel()
    titulo = QLabel(objectName="titulo_comando")
    titulo.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Preferred)
    h.addWidget(icono)
    h.addWidget(titulo, 1)
    for b in extras:
        h.addWidget(b)
    if cancelar is not None:
        cerrar = QToolButton(text="✕", toolTip=tooltip_cerrar)
        cerrar.clicked.connect(cancelar)
        cerrar.setFocusPolicy(Qt.NoFocus)
        h.addWidget(cerrar)
    return cab, icono, titulo


def fila_mensaje(ancho, alto_min=0):
    """Línea de estado de un panel: símbolo y texto (oculta mientras no hay texto). Con `alto_min` la línea queda
    reservada para que el panel no salte al aparecer o desaparecer un mensaje. Devuelve (zona, símbolo, texto)."""
    zona = QWidget()
    zona.setMinimumHeight(alto_min)
    h = QHBoxLayout(zona)
    h.setContentsMargins(10, 2, 10, 2)
    h.setSpacing(6)
    simbolo = QLabel()
    simbolo.setAlignment(Qt.AlignTop)
    texto = QLabel(objectName="mensaje_comando", wordWrap=True)
    texto.setMaximumWidth(ancho - 44)
    if not alto_min:        # nunca setVisible(True): sin padre todavía, se mostraría como una ventana suelta (B-136)
        zona.hide()
    simbolo.hide()
    texto.hide()
    h.addWidget(simbolo)
    h.addWidget(texto, 1)
    return zona, simbolo, texto


def poner_mensaje(simbolo, texto, contenido, tipo):
    """Muestra `contenido` en una línea hecha con `fila_mensaje`; `tipo` (ver TIPOS_MENSAJE) elige símbolo y color."""
    marca, color = TIPOS_MENSAJE[tipo]
    texto.setObjectName("mensaje_comando" if tipo in ("invalido", "error") else "aviso_comando")
    texto.setProperty("tipo", tipo)
    texto.setStyleSheet(f"color: {temas.color(color)};")
    simbolo.setStyleSheet(f"color: {temas.color(color)};")
    simbolo.setText(marca)
    texto.setText(contenido)
    texto.setVisible(bool(contenido))
    simbolo.setVisible(bool(contenido))
    zona = texto.parentWidget()
    if zona.minimumHeight() == 0:                    # sin alto reservado: la línea no ocupa lugar mientras no hay texto
        zona.setVisible(bool(contenido))


def armar_estado(panel, layout, ancho):
    """Las dos líneas de estado de un panel de boceto, en `layout`: la instrucción (`panel.guia`, con su símbolo) y debajo
    lo que está mal (`panel.mensaje`). Se llenan con `poner_estado`."""
    zona, panel.icono_guia, panel.guia = fila_mensaje(ancho)
    layout.addWidget(zona)
    zona, panel.icono_mensaje, panel.mensaje = fila_mensaje(ancho)
    layout.addWidget(zona)


def poner_estado(panel, guia, error):
    """Muestra la instrucción (➜) y el error (✖) en un panel armado con `armar_estado`; vacío oculta la línea."""
    poner_mensaje(panel.icono_guia, panel.guia, guia, "instruccion")
    poner_mensaje(panel.icono_mensaje, panel.mensaje, error, "invalido")
