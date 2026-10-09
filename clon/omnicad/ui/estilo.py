# -*- coding: utf-8 -*-
"""
Colores y hoja de estilo (QSS) de la interfaz.

Los valores salen de medir píxeles en las capturas de Fusion 360 que pasó el usuario
(cinta #f5f5f5, lienzo #2e3440, texto #3c3c3c, menús blancos con hover #f2f2f2).
Solo se reproduce el aspecto general; no se usa ningún recurso gráfico de Autodesk.
"""
FONDO = "#f5f5f5"          # barra superior, cinta, timeline
FONDO_DATOS = "#eeeeee"    # panel de datos
TARJETA = "#f7f7f7"
TEXTO = "#3c3c3c"
TEXTO_TENUE = "#8a8a8a"
BORDE = "#d4d4d4"
ACENTO = "#0696d7"
HOVER = "#e6f1fa"
LIENZO = "#2e3440"
LIENZO_RGB = (0x2D / 255, 0x32 / 255, 0x3F / 255)        # medido en el video de Fusion 2026 (tema oscuro)

QSS = f"""
* {{ font-family: "Segoe UI"; font-size: 9pt; color: {TEXTO}; }}
QMainWindow, #barra_app, #cinta, #barra_timeline {{ background: {FONDO}; }}
QToolTip {{ background: #4a4a4a; color: #ffffff; border: 0; padding: 6px 8px; }}

QMenu {{ background: #ffffff; border: 1px solid #c8c8c8; padding: 2px 0; }}
QMenu::item {{ padding: 4px 28px 4px 26px; }}
QMenu::item:selected {{ background: #f2f2f2; }}
QMenu::item:disabled {{ color: #a8a8a8; }}
QMenu::separator {{ height: 1px; background: #6e6e6e; margin: 2px 4px; }}
QMenu::icon {{ padding-left: 4px; }}
QMenu::right-arrow {{ width: 8px; height: 8px; }}

QToolButton {{ border: 1px solid transparent; border-radius: 2px; background: transparent; padding: 1px; }}
QToolButton:hover {{ background: {HOVER}; border-color: #c5dff2; }}
QToolButton:checked {{ background: #d6eaf8; border-color: #9cc9ea; }}
QToolButton::menu-indicator {{ image: none; width: 0; }}

#pestana {{ border: 0; border-bottom: 2px solid transparent; border-radius: 0; padding: 2px 14px 1px 14px;
            font-size: 9pt; letter-spacing: 0.3px; }}
#pestana:hover {{ background: transparent; border-bottom-color: #bdbdbd; }}
#pestana:checked {{ background: transparent; border-bottom-color: {TEXTO}; }}
#titulo_grupo {{ font-size: 8pt; padding: 0 6px; border-radius: 0; }}
#espacio_trabajo {{ border: 1px solid #c8c8c8; border-radius: 4px; background: {FONDO};
                    font-size: 9pt; font-weight: 600; padding: 0 14px; }}
#espacio_trabajo:hover {{ background: {HOVER}; }}
#separador_grupo {{ background: #dcdcdc; }}

#pestana_doc {{ background: #ffffff; border: 1px solid {BORDE}; border-bottom: 0;
                border-top-left-radius: 3px; border-top-right-radius: 3px; padding: 3px 16px; }}

#panel_datos {{ background: {FONDO_DATOS}; }}
#panel_datos QListWidget {{ background: {FONDO_DATOS}; border: 0; }}
#panel_datos QListWidget::item {{ background: {TARJETA}; border: 1px solid #e2e2e2; margin: 4px 8px; }}
#panel_datos QListWidget::item:selected {{ background: {HOVER}; border-color: #9cc9ea; }}

#cabecera_navegador {{ background: {FONDO}; border: 1px solid #c8c8c8; }}
#cabecera_navegador QLabel {{ font-size: 8pt; letter-spacing: 0.3px; }}
#arbol_navegador {{ background: transparent; border: 0; }}

#barra_navegacion {{ background: {FONDO}; border: 1px solid #c8c8c8; }}
#barra_navegacion QToolButton {{ padding: 2px; }}

#barra_timeline QListWidget {{ background: transparent; border: 0; }}
#barra_timeline QListWidget::item {{ border-radius: 2px; }}
#barra_timeline QListWidget::item:selected {{ background: #cfe6f7; }}
#estado_timeline {{ color: {TEXTO_TENUE}; padding-right: 8px; }}

#dlg_preferencias QTreeWidget {{ border: 1px solid #d0d0d0; background: #ffffff; }}
#dlg_preferencias QTreeWidget::item {{ padding: 4px 2px; }}
#dlg_preferencias QTreeWidget::item:selected {{ background: #dbeefa; color: {TEXTO}; }}
#cabecera_pref {{ border: 1px solid #c8c8c8; background: #ffffff; padding: 3px; }}
#pagina_pref {{ border: 1px solid #c8c8c8; background: #ffffff; }}
#boton_primario {{ background: {ACENTO}; color: #ffffff; border: 1px solid {ACENTO}; padding: 4px 14px; }}
#boton_primario:hover {{ background: #0a84bd; }}
"""
