# -*- coding: utf-8 -*-
"""
Sistema de temas de la interfaz: colores como datos, hoja de estilo (QSS) generada y temas del usuario.

  - Un tema es un dict de «tokens» de color (`#rrggbb`): superficies, textos, bordes, estados, menús, la vista 3D.
  - Hay cinco temas incluidos (`INCLUIDOS`); el de fábrica es `oscuro_moderno`. «clasico» conserva el aspecto de las
    primeras versiones (medido de las capturas de Fusion que pasó el usuario).
  - El QSS sale de UNA plantilla (`PLANTILLA_QSS`) y de los tokens: ningún color suelto en otro lado de la
    interfaz. Los widgets que dibujan a mano (navegador, menú radial, visor 3D) leen `activo()` al pintar.
  - Temas del usuario: archivos `.json` en la carpeta de temas (`carpeta_temas()`): `{"nombre": ..., "base": ...,
    "colores": {...}}`. Los colores que falten se toman de la base. Un archivo inválido se ignora y se avisa.
  - Cambiar de tema es inmediato: `activar()` + `aplicar_a_app()`; quien necesita reaccionar (el visor 3D) se
    anota con `observar()`.

Este módulo no importa Qt al cargarse (solo `aplicar_a_app` y `paleta` lo hacen, al usarse).
"""
import json
import os
import re
from pathlib import Path
from string import Template

from .. import carpeta_datos

DEFECTO = "oscuro_moderno"
PREFIJO_USUARIO = "usuario:"
VAR_CARPETA = "OMNICAD_TEMAS_DIR"        # reemplaza la carpeta de temas del usuario (pruebas, capturas)
MIN_CONTRASTE = 4.5                       # WCAG AA para texto normal

# Orden y significado de los tokens (también es la lista de claves válidas de un tema de usuario).
DESCRIPCION_COLORES = {
    "fondo": "barra superior, cinta de comandos y línea de tiempo",
    "panel": "panel de datos y páginas de diálogos",
    "panel_cabecera": "cabeceras de paneles (Navegador)",
    "tarjeta": "tarjetas de la lista de proyectos recientes",
    "entrada": "campos de texto, listas y árboles",
    "boton": "botones normales",
    "flotante": "paneles flotantes sobre la vista (comandos, comentarios, paleta de boceto, avisos)",
    "flotante_cabecera": "cabecera de los paneles flotantes",
    "texto": "texto normal",
    "texto_tenue": "texto secundario (notas, fechas, estado)",
    "texto_inactivo": "texto de lo que está desactivado",
    "enlace": "enlaces y texto de lo elegido en un comando",
    "borde": "bordes de paneles y botones",
    "borde_suave": "separadores finos",
    "acento": "color de marca (subrayado de pestañas, selección)",
    "hover": "fondo al pasar el ratón por un botón",
    "hover_borde": "borde al pasar el ratón por un botón",
    "activo": "fondo de un botón marcado",
    "activo_borde": "borde de un botón marcado",
    "seleccion": "fondo de lo elegido en listas y árboles",
    "seleccion_borde": "borde de lo elegido",
    "seleccion_texto": "texto de lo elegido",
    "boton_primario": "fondo del botón principal (Aceptar)",
    "boton_primario_hover": "fondo del botón principal al pasar el ratón",
    "boton_primario_texto": "texto del botón principal",
    "menu_fondo": "menús desplegables",
    "menu_borde": "borde de los menús",
    "menu_hover": "fila resaltada de un menú",
    "menu_separador": "línea separadora de los menús",
    "tooltip_fondo": "globos de ayuda",
    "tooltip_texto": "texto de los globos de ayuda",
    "error": "texto de errores",
    "aviso": "texto de avisos",
    "ok": "texto de lo que salió bien",
    "campo_error": "fondo de un campo con un valor inválido",
    "nav_fila": "fila del Navegador flotante",
    "nav_flecha": "flechitas de plegado del Navegador",
    "visor_arriba": "fondo de la vista 3D (parte de arriba)",
    "visor_abajo": "fondo de la vista 3D (parte de abajo)",
    "rejilla": "líneas de la rejilla de la vista 3D",
}
CLAVES_COLOR = tuple(DESCRIPCION_COLORES)


def _tema(nombre, **colores):
    faltan = set(CLAVES_COLOR) - set(colores)
    sobran = set(colores) - set(CLAVES_COLOR)
    assert not faltan and not sobran, (nombre, faltan, sobran)
    return {"nombre": nombre, "colores": colores}


INCLUIDOS = {
    # Gris carbón con acento naranja (referencia 1 de docs/diseno/referencia_4_temas.webp).
    "oscuro_moderno": _tema(
        "Oscuro moderno",
        fondo="#1c232c", panel="#161d26", panel_cabecera="#232c37", tarjeta="#212a35", entrada="#202934",
        boton="#2a3441", flotante="#151c24", flotante_cabecera="#1d2631",
        texto="#e8ecf1", texto_tenue="#9aa5b4", texto_inactivo="#5d6877", enlace="#5aa9ff",
        borde="#36424f", borde_suave="#28323d", acento="#ff7d0a", hover="#28323e", hover_borde="#3b4756",
        activo="#3b2c20", activo_borde="#ff7d0a", seleccion="#40301f", seleccion_borde="#ff7d0a",
        seleccion_texto="#ffffff", boton_primario="#ff7d0a", boton_primario_hover="#ff9233",
        boton_primario_texto="#1a1206", menu_fondo="#1a212a", menu_borde="#36424f", menu_hover="#2b3541",
        menu_separador="#3a4654", tooltip_fondo="#0f1419", tooltip_texto="#e8ecf1", error="#ff8a80",
        aviso="#ffc857", ok="#6fdc8c", campo_error="#5c2a2d", nav_fila="#232c37", nav_flecha="#8b97a8",
        visor_arriba="#15202e", visor_abajo="#202b3e", rejilla="#6f8cb8"),
    # Blanco con acento azul (referencia 2).
    "claro_moderno": _tema(
        "Claro moderno",
        fondo="#f1f5f9", panel="#f8fafb", panel_cabecera="#e9eef3", tarjeta="#ffffff", entrada="#ffffff",
        boton="#eef2f6", flotante="#fbfcfd", flotante_cabecera="#eef2f6",
        texto="#1f2933", texto_tenue="#5b6573", texto_inactivo="#a3acb8", enlace="#1a63d1",
        borde="#cdd5de", borde_suave="#e1e7ee", acento="#2f80ed", hover="#e6eef8", hover_borde="#c2d6ee",
        activo="#d9e8fb", activo_borde="#8bb4ee", seleccion="#d9e8fb", seleccion_borde="#8bb4ee",
        seleccion_texto="#14202e", boton_primario="#1d6ae5", boton_primario_hover="#1858c0",
        boton_primario_texto="#ffffff", menu_fondo="#ffffff", menu_borde="#cdd5de", menu_hover="#edf2f8",
        menu_separador="#d5dce5", tooltip_fondo="#2b3340", tooltip_texto="#f4f6f8", error="#c62828",
        aviso="#8a5a00", ok="#1b6e20", campo_error="#ffd9d9", nav_fila="#ffffff", nav_flecha="#7b8794",
        visor_arriba="#e6ebf0", visor_abajo="#f2f5f8", rejilla="#7d8ea3"),
    # Azul marino con acento azul (referencia 3).
    "azul_profesional": _tema(
        "Azul profesional",
        fondo="#0c2540", panel="#081f38", panel_cabecera="#12304f", tarjeta="#102c49", entrada="#0f2c4c",
        boton="#16355a", flotante="#081f38", flotante_cabecera="#0e2a47",
        texto="#e6eef8", texto_tenue="#9db4cf", texto_inactivo="#5c7391", enlace="#6db3ff",
        borde="#1f4a78", borde_suave="#173a5f", acento="#268afe", hover="#15385f", hover_borde="#24578c",
        activo="#1a4a7e", activo_borde="#268afe", seleccion="#1c4b80", seleccion_borde="#268afe",
        seleccion_texto="#ffffff", boton_primario="#268afe", boton_primario_hover="#4aa0ff",
        boton_primario_texto="#04101e", menu_fondo="#0b2441", menu_borde="#1f4a78", menu_hover="#16406b",
        menu_separador="#244d7a", tooltip_fondo="#041525", tooltip_texto="#e6eef8", error="#ff8a80",
        aviso="#ffc857", ok="#6fdc8c", campo_error="#5c2a35", nav_fila="#12304f", nav_flecha="#8fb0d6",
        visor_arriba="#10294a", visor_abajo="#163a62", rejilla="#4a8fe8"),
    # Beige claro con acento naranja (referencia 4).
    "minimalista": _tema(
        "Minimalista",
        fondo="#f7f3ed", panel="#f9f5f0", panel_cabecera="#efe9df", tarjeta="#fffdf9", entrada="#fffdf9",
        boton="#f1ebe2", flotante="#fbf8f2", flotante_cabecera="#efe9df",
        texto="#2b2620", texto_tenue="#6d6558", texto_inactivo="#b0a89a", enlace="#a94f00",
        borde="#d8cfc2", borde_suave="#e8e0d3", acento="#fd8101", hover="#f2e9dc", hover_borde="#e2d3bd",
        activo="#fbe3c8", activo_borde="#fd8101", seleccion="#fbe3c8", seleccion_borde="#fd8101",
        seleccion_texto="#2b2620", boton_primario="#fd8101", boton_primario_hover="#ff9a33",
        boton_primario_texto="#2b1700", menu_fondo="#fffdf9", menu_borde="#d8cfc2", menu_hover="#f5ecdf",
        menu_separador="#ddd3c4", tooltip_fondo="#38312a", tooltip_texto="#f7f3ed", error="#b3261e",
        aviso="#8a5a00", ok="#1b6e20", campo_error="#ffd9d0", nav_fila="#fffdf9", nav_flecha="#9a8b76",
        visor_arriba="#f1ebe2", visor_abajo="#f9f5ef", rejilla="#9a8b76"),
    # El aspecto de las primeras versiones: cinta gris clara y lienzo azul pizarra.
    "clasico": _tema(
        "Clásico",
        fondo="#f5f5f5", panel="#eeeeee", panel_cabecera="#f5f5f5", tarjeta="#f7f7f7", entrada="#ffffff",
        boton="#f0f0f0", flotante="#ffffff", flotante_cabecera="#f0f0f0",
        texto="#3c3c3c", texto_tenue="#6a6a6a", texto_inactivo="#a8a8a8", enlace="#0b6bcb",
        borde="#c8c8c8", borde_suave="#dcdcdc", acento="#0696d7", hover="#e6f1fa", hover_borde="#c5dff2",
        activo="#d6eaf8", activo_borde="#9cc9ea", seleccion="#cfe6f7", seleccion_borde="#9cc9ea",
        seleccion_texto="#3c3c3c", boton_primario="#0577b0", boton_primario_hover="#046a9c",
        boton_primario_texto="#ffffff", menu_fondo="#ffffff", menu_borde="#c8c8c8", menu_hover="#f2f2f2",
        menu_separador="#6e6e6e", tooltip_fondo="#4a4a4a", tooltip_texto="#ffffff", error="#b00020",
        aviso="#7a6000", ok="#1b6e20", campo_error="#ffd9d9", nav_fila="#f5f5f5", nav_flecha="#d6d9de",
        visor_arriba="#2d323f", visor_abajo="#2d323f", rejilla="#9ea8bd"),
}

# Pares (texto, fondo) que tienen que dar al menos MIN_CONTRASTE para que todo se lea.
PARES_CONTRASTE = (
    ("texto", "fondo"), ("texto", "panel"), ("texto", "panel_cabecera"), ("texto", "tarjeta"),
    ("texto", "entrada"), ("texto", "boton"), ("texto", "flotante"), ("texto", "flotante_cabecera"),
    ("texto_tenue", "fondo"), ("texto_tenue", "panel"), ("texto_tenue", "tarjeta"), ("texto_tenue", "flotante"),
    ("enlace", "panel"), ("enlace", "flotante"), ("texto", "hover"), ("texto", "activo"),
    ("seleccion_texto", "seleccion"), ("texto", "menu_fondo"), ("texto", "menu_hover"),
    ("boton_primario_texto", "boton_primario"), ("boton_primario_texto", "boton_primario_hover"),
    ("tooltip_texto", "tooltip_fondo"), ("error", "panel"), ("error", "flotante"), ("error", "fondo"),
    ("aviso", "panel"), ("aviso", "flotante"), ("aviso", "fondo"), ("ok", "panel"), ("ok", "flotante"),
    ("ok", "fondo"), ("texto", "campo_error"), ("texto", "nav_fila"),
)


class ErrorTema(ValueError):
    """Un archivo de tema que no se puede usar (JSON roto, no es un objeto…)."""


# ---------------------------------------------------------------- colores y contraste
_HEX = re.compile(r"#(?:[0-9a-fA-F]{3}|[0-9a-fA-F]{6})")


def normalizar_color(valor):
    """'#ABC' / '#AABBCC' → '#aabbcc'. Cualquier otra cosa → None."""
    if not isinstance(valor, str) or not _HEX.fullmatch(valor.strip()):
        return None
    v = valor.strip().lower()
    return "#" + "".join(c * 2 for c in v[1:]) if len(v) == 4 else v


def rgb_f(color):
    """'#rrggbb' → (r, g, b) en 0..1 (lo que usa el visor OpenGL)."""
    return tuple(int(color[i:i + 2], 16) / 255 for i in (1, 3, 5))


def luminancia(color):
    """Luminancia relativa WCAG de un '#rrggbb'."""
    def canal(c):
        return c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4
    r, g, b = (canal(c) for c in rgb_f(color))
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def razon_contraste(a, b):
    """Razón de contraste WCAG entre dos colores (1 a 21)."""
    la, lb = sorted((luminancia(a), luminancia(b)), reverse=True)
    return (la + 0.05) / (lb + 0.05)


def contraste_bajo(colores, minimo=MIN_CONTRASTE):
    """[(texto, fondo, razón)] de los pares de `PARES_CONTRASTE` que no llegan al mínimo."""
    return [(t, f, razon_contraste(colores[t], colores[f])) for t, f in PARES_CONTRASTE
            if razon_contraste(colores[t], colores[f]) < minimo]


# ---------------------------------------------------------------- hoja de estilo
PLANTILLA_QSS = Template("""
* { font-family: "Segoe UI"; font-size: 9pt; color: $texto; }
*:disabled { color: $texto_inactivo; }
QMainWindow, #barra_app, #cinta, #barra_timeline { background: $fondo; }
QToolTip { background: $tooltip_fondo; color: $tooltip_texto; border: 0; padding: 6px 8px; }

QMenu { background: $menu_fondo; border: 1px solid $menu_borde; padding: 2px 0; }
QMenu::item { padding: 4px 28px 4px 26px; }
QMenu::item:selected { background: $menu_hover; }
QMenu::item:disabled { color: $texto_inactivo; }
QMenu::separator { height: 1px; background: $menu_separador; margin: 2px 4px; }
QMenu::icon { padding-left: 4px; }
QMenu::right-arrow { width: 8px; height: 8px; }

QToolButton { border: 1px solid transparent; border-radius: 2px; background: transparent; padding: 1px; }
QToolButton:hover { background: $hover; border-color: $hover_borde; }
QToolButton:checked { background: $activo; border-color: $activo_borde; }
QToolButton::menu-indicator { image: none; width: 0; }

QScrollBar:vertical { background: transparent; width: 12px; margin: 0; }
QScrollBar:horizontal { background: transparent; height: 12px; margin: 0; }
QScrollBar::handle:vertical { background: $texto_inactivo; min-height: 24px; border-radius: 4px; margin: 2px; }
QScrollBar::handle:horizontal { background: $texto_inactivo; min-width: 24px; border-radius: 4px; margin: 2px; }
QScrollBar::handle:hover { background: $texto_tenue; }
QScrollBar::add-line, QScrollBar::sub-line { width: 0; height: 0; border: 0; background: transparent; }
QScrollBar::add-page, QScrollBar::sub-page { background: transparent; }

#pestana { border: 0; border-bottom: 2px solid transparent; border-radius: 0; padding: 2px 14px 1px 14px;
           font-size: 9pt; letter-spacing: 0.3px; }
#pestana:hover { background: transparent; border-bottom-color: $borde; }
#pestana:checked { background: transparent; border-bottom-color: $acento; }
#titulo_grupo { font-size: 8pt; padding: 0 6px; border-radius: 0; }
#boton_cinta { font-size: 8pt; padding: 3px 4px 1px 4px; border-radius: 4px; }
#espacio_trabajo { border: 1px solid $boton_primario; border-radius: 4px; background: $boton_primario;
                   color: $boton_primario_texto; font-size: 9pt; font-weight: 600; padding: 0 14px; }
#espacio_trabajo:hover { background: $boton_primario_hover; }  /* relleno con el acento, como en docs/diseno/ */
#separador_grupo { background: $borde_suave; }
#caja_herramientas { background: $flotante; border: 1px solid $borde; border-radius: 6px; }
#titulo_caja { font-size: 8pt; letter-spacing: 0.4px; color: $texto_tenue; }
#atajos_caja, #resultados_caja { background: transparent; border: 0; }
#atajos_caja::item { border-radius: 4px; padding: 2px; }
#atajos_caja::item:hover { background: $hover; }
#atajos_caja::item:selected { background: transparent; color: $texto; }
#resultados_caja::item { border-radius: 3px; }
#resultados_caja::item:selected { background: $menu_hover; }
#vacio_caja, #atajo_teclado { color: $texto_tenue; }
#chinche:checked { background: $activo; border-color: $activo_borde; }

#pestana_doc { background: $entrada; border: 1px solid $borde; border-bottom: 0;
               border-top-left-radius: 3px; border-top-right-radius: 3px; padding: 3px 16px; }

#panel_datos { background: $panel; }
#panel_datos QListWidget { background: $panel; border: 0; }
#panel_datos QListWidget::item { background: $tarjeta; border: 1px solid $borde_suave; margin: 4px 8px; }
#panel_datos QListWidget::item:selected { background: $seleccion; border-color: $seleccion_borde; }
#panel_datos #miniatura { background: $entrada; }

#cabecera_navegador { background: $panel_cabecera; border: 1px solid $borde; }
#cabecera_navegador QLabel { font-size: 8pt; letter-spacing: 0.3px; }
#arbol_navegador { background: transparent; border: 0; }

#barra_navegacion { background: $fondo; border: 1px solid $borde; }
#barra_navegacion QToolButton { padding: 2px; }
#separador_barra { background: $borde; }

#barra_timeline QListWidget { background: transparent; border: 0; }
#barra_timeline QListWidget::item { border-radius: 2px; }
#barra_timeline QListWidget::item:selected { background: $seleccion; }
#estado_timeline { color: $texto_tenue; padding-right: 8px; }
#selector_unidades { color: $texto_tenue; padding: 2px 8px; border-radius: 4px; }
#selector_unidades:hover { color: $texto; }

#dlg_preferencias QTreeWidget { border: 1px solid $borde; background: $entrada; }
#dlg_preferencias QTreeWidget::item { padding: 4px 2px; }
#dlg_preferencias QTreeWidget::item:selected { background: $seleccion; color: $seleccion_texto; }
#cabecera_pref { border: 1px solid $borde; background: $flotante; padding: 3px; }
#pagina_pref { border: 1px solid $borde; background: $flotante; }
#boton_primario { background: $boton_primario; color: $boton_primario_texto; border: 1px solid $boton_primario;
                  padding: 4px 14px; }
#boton_primario:hover { background: $boton_primario_hover; }

#panel_comando { background: $flotante; border: 1px solid $borde; }
#cabecera_comando { background: $flotante_cabecera; border-bottom: 1px solid $borde_suave; }
#titulo_comando { font-weight: 600; letter-spacing: 0.3px; }
#panel_comando QLabel#etiqueta_cmd { color: $texto; }
#seleccion_cmd { text-align: left; padding: 3px 8px; border: 1px solid $borde; background: $entrada; }
#seleccion_cmd[activa="true"] { border: 1px solid $acento; background: $activo; color: $enlace; }
#seleccion_cmd[lleno="true"] { color: $texto; }
#panel_comando QLineEdit, #panel_comando QComboBox, #panel_comando QSpinBox { padding: 2px 4px; }
#mensaje_comando { color: $error; }
#aviso_comando { color: $aviso; }

#panel_comentarios { background: $flotante; border: 1px solid $borde; }
#panel_comentarios QLabel { color: $texto_tenue; font-size: 10px; letter-spacing: 0.5px; }
#panel_comentarios QToolButton { border: none; color: $texto_tenue; font-size: 13px; padding: 0 4px; }
#panel_comentarios QListWidget { border: none; border-top: 1px solid $borde_suave; font-size: 11px; }

#paleta_boceto { background: $fondo; border: 1px solid $borde; }
#paleta_boceto QLabel { font-size: 9pt; }
#entrada_valor { background: $entrada; border: 1px solid $acento; border-radius: 2px; }
#entrada_valor QLineEdit { border: 0; padding: 1px 3px; min-width: 70px; }

#panel_flotante { background: $flotante; border: 1px solid $borde; }
#titulo_panel { background: $flotante_cabecera; border-bottom: 1px solid $borde_suave; }
#titulo_panel QLabel { font-weight: 600; letter-spacing: 0.4px; }
#panel_flotante QGroupBox { font-weight: 600; }
#galeria_render { background: $fondo; border-top: 1px solid $borde; }
#galeria_render QListWidget { background: transparent; border: 0; }

#AvisoFlotante { background: $flotante; border: 1px solid $borde; border-radius: 2px; }
#AvisoFlotante QLabel { background: transparent; }
#AvisoFlotante QToolButton { border: none; color: $texto_tenue; font-size: 14px; }
#lista_radial { background: $menu_fondo; border: 1px solid $menu_borde; }
#lista_radial #linea_radial { border: none; border-top: 1px solid $borde_suave; margin: 3px 6px 0 6px; }

QLabel[rol="tenue"] { color: $texto_tenue; }
QLabel[rol="titulo"] { font-weight: bold; }
QLabel[rol="encabezado"] { font-size: 8pt; letter-spacing: 0.4px; color: $texto_tenue; }
QLabel[rol="seccion"] { font-weight: 600; padding-top: 4px; border-bottom: 1px solid $borde_suave; }
QLabel[rol="error"] { color: $error; }
QLabel[rol="aviso"] { color: $aviso; }
QLabel[rol="ok"] { color: $ok; }
#indicador_agente[rol="esperando"] { color: $texto_tenue; padding: 0 10px; }
#indicador_agente[rol="conectado"] { color: $ok; padding: 0 8px; font-weight: bold; }
""")


def generar_qss(colores):
    """Hoja de estilo de la aplicación para un dict de tokens COMPLETO. Falta un token → KeyError."""
    return PLANTILLA_QSS.substitute(colores)


def paleta(colores):
    """QPalette equivalente: lo que no pinta el QSS (casillas, flechas, scrollbars, diálogos estándar)."""
    from PySide6.QtGui import QColor, QPalette
    c = {k: QColor(v) for k, v in colores.items()}
    p = QPalette()
    R = QPalette
    for rol, clave in ((R.Window, "fondo"), (R.WindowText, "texto"), (R.Base, "entrada"), (R.AlternateBase, "panel"),
                       (R.Text, "texto"), (R.Button, "boton"), (R.ButtonText, "texto"), (R.BrightText, "texto"),
                       (R.Highlight, "seleccion"), (R.HighlightedText, "seleccion_texto"), (R.Link, "enlace"),
                       (R.LinkVisited, "enlace"), (R.ToolTipBase, "tooltip_fondo"), (R.ToolTipText, "tooltip_texto"),
                       (R.PlaceholderText, "texto_tenue"), (R.Mid, "borde"), (R.Midlight, "borde_suave"),
                       (R.Light, "hover"), (R.Dark, "borde"), (R.Shadow, "tooltip_fondo")):
        p.setColor(rol, c[clave])
    for rol in (R.WindowText, R.Text, R.ButtonText):
        p.setColor(R.Disabled, rol, c["texto_inactivo"])
    p.setColor(R.Disabled, R.HighlightedText, c["texto_inactivo"])
    return p


# ---------------------------------------------------------------- temas del usuario
def carpeta_temas(crear=False):
    """Carpeta de los temas del usuario (`OMNICAD_TEMAS_DIR` la reemplaza). Con `crear` se asegura que exista."""
    carpeta = Path(os.environ[VAR_CARPETA]) if os.environ.get(VAR_CARPETA) else carpeta_datos() / "temas"
    if crear:
        carpeta.mkdir(parents=True, exist_ok=True)
    return carpeta


def completar(base, colores):
    """Tokens de `base` (clave de un tema incluido) pisados por los válidos de `colores`.
    Devuelve (colores completos, avisos): las claves desconocidas y los valores que no son '#rrggbb' se ignoran."""
    if base not in INCLUIDOS:
        raise KeyError(base)
    salida, avisos = dict(INCLUIDOS[base]["colores"]), []
    if not isinstance(colores, dict):
        return salida, ["«colores» tiene que ser un objeto {nombre: \"#rrggbb\"}"]
    for clave, valor in colores.items():
        if clave not in DESCRIPCION_COLORES:
            avisos.append(f"el color «{clave}» no existe (se ignora)")
            continue
        color = normalizar_color(valor)
        if color is None:
            avisos.append(f"«{clave}»: «{valor}» no es un color #rrggbb (se usa el de la base)")
            continue
        salida[clave] = color
    return salida, avisos


def tema_desde_dict(datos, clave, nombre_defecto):
    """Valida el contenido de un archivo de tema. Devuelve (tema, avisos) o lanza ErrorTema."""
    if not isinstance(datos, dict):
        raise ErrorTema("el archivo tiene que ser un objeto JSON {\"nombre\": ..., \"base\": ..., \"colores\": {...}}")
    avisos = []
    base = datos.get("base", DEFECTO)
    if base not in INCLUIDOS:
        avisos.append(f"la base «{base}» no existe; se usa «{DEFECTO}» (bases: {', '.join(INCLUIDOS)})")
        base = DEFECTO
    colores, extra = completar(base, datos.get("colores", {}))
    nombre = datos.get("nombre")
    nombre = nombre.strip() if isinstance(nombre, str) and nombre.strip() else nombre_defecto
    return {"clave": clave, "nombre": nombre, "base": base, "colores": colores, "usuario": True}, avisos + extra


def leer_archivo(ruta):
    """Un archivo de tema → (tema, avisos). Lanza ErrorTema si no se puede usar."""
    ruta = Path(ruta)
    try:
        datos = json.loads(ruta.read_text(encoding="utf-8-sig"))
    except OSError as e:
        raise ErrorTema(f"no se pudo leer ({e.strerror or e})") from None
    except ValueError as e:
        raise ErrorTema(f"no es un JSON válido ({e})") from None
    return tema_desde_dict(datos, PREFIJO_USUARIO + ruta.stem, ruta.stem)


def temas_usuario(carpeta=None):
    """Los temas de la carpeta del usuario: ({clave: tema}, avisos). Un archivo inválido se ignora con un aviso."""
    carpeta = Path(carpeta) if carpeta is not None else carpeta_temas()
    temas, avisos = {}, []
    if not carpeta.is_dir():
        return temas, avisos
    for ruta in sorted(carpeta.glob("*.json"), key=lambda r: r.name.lower()):
        try:
            tema, extra = leer_archivo(ruta)
        except ErrorTema as e:
            avisos.append(f"Tema «{ruta.name}» ignorado: {e}")
            continue
        temas[tema["clave"]] = tema
        avisos += [f"Tema «{ruta.name}»: {a}" for a in extra]
    return temas, avisos


def disponibles(carpeta=None):
    """[(clave, nombre, es_del_usuario)] de los temas elegibles (incluidos primero) y los avisos al leer la carpeta."""
    usuario, avisos = temas_usuario(carpeta)
    lista = [(k, t["nombre"], False) for k, t in INCLUIDOS.items()]
    return lista + [(k, t["nombre"], True) for k, t in usuario.items()], avisos


def resolver(clave, carpeta=None):
    """Tema completo de una clave: (tema, avisos). Una clave desconocida cae al tema de fábrica con un aviso."""
    usuario, avisos = temas_usuario(carpeta)
    if clave in INCLUIDOS:
        t = INCLUIDOS[clave]
        return {"clave": clave, "nombre": t["nombre"], "base": clave, "colores": dict(t["colores"]),
                "usuario": False}, avisos
    if clave in usuario:
        return usuario[clave], avisos
    t = INCLUIDOS[DEFECTO]
    return ({"clave": DEFECTO, "nombre": t["nombre"], "base": DEFECTO, "colores": dict(t["colores"]),
             "usuario": False},
            avisos + [f"No se encontró el tema «{clave}»: se usa «{t['nombre']}»."])


def exportar_plantilla(ruta, clave=None, nombre=None):
    """Escribe un tema como archivo JSON con TODOS sus colores, para que el usuario lo edite y cree el suyo."""
    tema, _ = resolver(clave or clave_activa())
    nombre = nombre or f"Mi tema ({tema['nombre']})"
    contenido = {"nombre": nombre, "base": tema["base"], "colores": tema["colores"]}
    ruta = Path(ruta)
    ruta.parent.mkdir(parents=True, exist_ok=True)
    ruta.write_text(json.dumps(contenido, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return ruta


def ruta_plantilla_nueva(carpeta=None):
    """Un nombre de archivo libre en la carpeta de temas (mi_tema.json, mi_tema_2.json…)."""
    carpeta = Path(carpeta) if carpeta is not None else carpeta_temas()
    ruta, n = carpeta / "mi_tema.json", 2
    while ruta.exists():
        ruta, n = carpeta / f"mi_tema_{n}.json", n + 1
    return ruta


# ---------------------------------------------------------------- tema activo
_activo = dict(resolver(DEFECTO, Path(os.devnull))[0])          # (el valor de fábrica; la app lo cambia con activar)
_observadores = []


def activo():
    """Los tokens del tema ACTIVO (dict clave → '#rrggbb'). Los widgets que pintan a mano lo leen en cada pintado."""
    return _activo["colores"]


def color(clave):
    return _activo["colores"][clave]


def clave_activa():
    return _activo["clave"]


def nombre_activo():
    return _activo["nombre"]


def observar(funcion):
    """`funcion()` se llama cada vez que cambia el tema activo (la vista 3D actualiza su fondo)."""
    _observadores.append(funcion)
    return funcion


def activar(clave, carpeta=None):
    """Elige el tema `clave` (incluido o del usuario). Devuelve los avisos (archivos inválidos, tema no encontrado)."""
    global _activo
    tema, avisos = resolver(clave, carpeta)
    _activo = tema
    for f in list(_observadores):
        f()
    return avisos


def poner_rol(widget, rol):
    """Le da a un widget su «rol» de estilo (ver QLabel[rol=...] en la plantilla) y lo repinta con el QSS vigente."""
    widget.setProperty("rol", rol)
    estilo = widget.style()
    estilo.unpolish(widget)
    estilo.polish(widget)


def qss_activo():
    return generar_qss(activo())


def aplicar_a_app(app):
    """Estilo Fusion (respeta la paleta en todos los widgets) + paleta + QSS del tema activo en la aplicación."""
    from . import iconos_tema
    iconos_tema.instalar()          # los íconos oscuros se ven sobre un tema oscuro (se fija con el tema de arranque)
    if app.style().objectName().lower() != "fusion":
        app.setStyle("Fusion")
    app.setPalette(paleta(activo()))
    app.setStyleSheet(qss_activo())
