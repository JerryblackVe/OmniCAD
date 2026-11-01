# -*- coding: utf-8 -*-
"""Paneles de herramienta en CADA tema disponible (y con el tamaño de letra al 125 y 150 %, que es lo que cambia en la
interfaz con la escala): abre Extruir (con «Más opciones» abierta y un valor inválido), el Patrón (cambio de modo) y la
Multitransformación y el diálogo Renderizar, captura cada uno y comprueba el contraste de los colores de mensaje (instrucción, inválido,
advertencia) contra el fondo del panel, y que nada se recorte (sin desborde horizontal, entra en el lienzo).
    paneles_temas.py   → `evidencias/ui_paneles_2026-10-31/temas/<tema>_<pct>/*.png`."""
import arnes as A
import escena
from omnicad.ui import render, temas
from omnicad.ui.comando import hit_desde_ref
from omnicad.ui.comandos import CATALOGO
from omnicad.ui.formulario import TIPOS_MENSAJE
from PySide6.QtWidgets import QCheckBox, QLabel, QPushButton, QToolButton

AR = "PANELES·temas"
CARPETA = A.SALIDA.parent / "ui_paneles_2026-10-31" / "temas"
s, ids = escena.construir()
app, v = A.iniciar(s.doc, 1280, 720)
A.esperar(300)
caja = hit_desde_ref({"tipo": "cuerpo", "cuerpo": ids["caja"]}, s.doc.estado_final)


def abrir(clave, **valores):
    if v.panel is not None:
        v.panel.cancelar()
        A.esperar(60)
    panel = v.ejecutar_comando(CATALOGO[clave](), valores=valores or None)
    A.esperar(150)
    return panel


def revisar(tema, pct):
    carpeta = CARPETA / f"{tema}_{pct}"
    carpeta.mkdir(parents=True, exist_ok=True)
    for tipo in ("instruccion", "invalido", "aviso"):                      # contraste de los tres mensajes que se leen más
        _, token = TIPOS_MENSAJE[tipo]
        razon = temas.razon_contraste(temas.color(token), temas.color("flotante"))
        A.reg(AR, f"{tema} {pct} % · contraste de «{tipo}» sobre el panel", razon >= temas.MIN_CONTRASTE, f"{razon:.2f}")
    p = abrir("extruir")
    p.seccion.boton.setChecked(True)
    p.set_valor("conicidad", "xx")
    p._calcular_previa()
    A.esperar(100)
    p.grab().save(str(carpeta / "extruir_invalido.png"))
    A.reg(AR, f"{tema} {pct} % · Extruir con valor inválido: sin desborde y dentro del lienzo",
          p.desplazador.widget().minimumSizeHint().width() <= p.desplazador.viewport().width() + 1
          and v.area.rect().contains(p.geometry()), f"{p.width()}x{p.height()}")
    p = abrir("patron_rectangular_3d", cuerpos=[caja])
    p.set_valor("forma", "circular")
    A.esperar(100)
    p.grab().save(str(carpeta / "patron_circular.png"))
    A.reg(AR, f"{tema} {pct} % · Patrón: la cabecera dice «{p.titulo.text()}»", p.titulo.text() == "PATRÓN CIRCULAR", "")
    p = abrir("multitransformar", cuerpos=[caja])
    p.grab().save(str(carpeta / "multitransformar.png"))
    A.reg(AR, f"{tema} {pct} % · Multitransformación entra en el lienzo", v.area.rect().contains(p.geometry()),
          f"{p.width()}x{p.height()}")
    p.cancelar()
    revisar_renderizar(tema, pct, carpeta)


def revisar_renderizar(tema, pct, carpeta):
    """El diálogo Renderizar con la letra grande: el aviso largo de carpeta inexistente, ningún texto cortado y todo en pantalla."""
    d = render.DialogoRenderizar(v, (1280, 720), carpeta / "render.png")
    d.ruta.setText("Z:/una_carpeta_que_no_existe_y_tiene_un_nombre_bastante_largo/render.png")
    d._mirar_carpeta()
    d.show()
    A.esperar(150)
    cortados = [w.text() for clase in (QLabel, QCheckBox, QPushButton, QToolButton) for w in d.findChildren(clase)
                if w.isVisible() and not (isinstance(w, QLabel) and w.wordWrap()) and w.sizeHint().width() > w.width() + 1]
    aviso = d.mensaje
    A.reg(AR, f"{tema} {pct} % · Renderizar: ningún texto cortado ni desborde horizontal",
          not cortados and d.minimumSizeHint().width() <= d.width(), f"{d.width()}x{d.height()} · cortados: {cortados}")
    A.reg(AR, f"{tema} {pct} % · Renderizar: el aviso largo se lee entero (con ⚠) y el diálogo entra en la pantalla",
          aviso.isVisible() and d.icono_mensaje.text() == "⚠" and aviso.heightForWidth(aviso.width()) <= aviso.height()
          and d.height() <= d.screen().availableGeometry().height(), f"{aviso.width()}x{aviso.height()} de {aviso.heightForWidth(aviso.width())}")
    d.grab().save(str(carpeta / "renderizar.png"))
    d.close()
    d.deleteLater()


def todo():
    lista, _ = temas.disponibles()
    for clave, nombre, _usuario in lista:
        for pct in (100, 125, 150):
            v.prefs["interfaz/tamano_pct"] = pct
            v.aplicar_tema(clave)
            A.esperar(200)
            revisar(clave, pct)
    v.prefs["interfaz/tamano_pct"] = 100
    v.aplicar_tema()


A.correr(AR, todo)
A.reg(AR, "no se escapó ninguna excepción dentro de un slot de Qt", not A.ERRORES, "; ".join(A.ERRORES)[:300])
A.guardar_registro("paneles_temas")
fallas = sum(1 for r in A.REGISTRO if not r["ok"])
print(f"=== {len(A.REGISTRO)} comprobaciones, {fallas} con ✗", flush=True)
