# -*- coding: utf-8 -*-
"""Inventario de los diálogos y paneles de herramienta que NO salen del catálogo de comandos (boceto, dibujo, animación,
administrar…): los abre sobre la ventana real, mide su tamaño frente a una pantalla de 1280x720 y busca lo que sobra
(desborde horizontal, botones fuera del diálogo, nada que desplace). Captura cada uno.
    dialogos_inventario.py [fase]      fase = «antes» o «despues» (carpeta de capturas), por defecto «despues».
Deja `evidencias/ui_paneles_2026-10-31/<fase>_dialogos/*.png` y `inventario_dialogos_<fase>.json`."""
import json
import sys

import arnes as A
import escena
from PySide6.QtWidgets import QAbstractButton, QScrollArea

FASE = sys.argv[1] if len(sys.argv) > 1 else "despues"
AR = f"DIÁLOGOS·{FASE}"
CARPETA = A.SALIDA.parent / "ui_paneles_2026-10-31" / f"{FASE}_dialogos"
CARPETA.mkdir(parents=True, exist_ok=True)
PANTALLA = (1280, 720 - 48)                 # el área útil de una pantalla 1280x720 con la barra de tareas

s, ids = escena.construir()
app, v = A.iniciar(s.doc, 1280, 720)
A.esperar(300)
est = s.doc.estado_final
boceto = next(iter(est.bocetos.values())).boceto
malla = [c for c in est.cuerpos.values() if c.tipo == "malla"]


def fabricas():
    from omnicad.ui import (administrar, animacion, aspectos_ui, dialogo_autorestringir, dialogo_parametros, dialogos, dibujo, guardar_malla,
                            mas_comando, modo_boceto, panel_patron, panel_simetria, panel_transformar, render)
    yield "boceto · panel Patrón", "panel_patron.PanelPatron", lambda: panel_patron.PanelPatron(v.area)
    yield "boceto · panel Simetría", "panel_simetria.PanelSimetria", lambda: panel_simetria.PanelSimetria(v.area)
    yield "boceto · panel Escala / Mover", "panel_transformar.PanelTransformar", lambda: panel_transformar.PanelTransformar(v.area)
    yield "boceto · panel Carácter (texto)", "modo_boceto.PanelCaracter", lambda: modo_boceto.PanelCaracter(v.area)
    yield "render · Renderizar", "render.DialogoRenderizar", lambda: render.DialogoRenderizar(v, (1280, 720), "render.png")
    yield "render · Capturar imagen", "render.DialogoRenderizar",         lambda: render.DialogoRenderizar(v, (1280, 720), "captura.png", captura=True)
    yield "render · Lienzo", "render.DialogoLienzo", lambda: render.DialogoLienzo(v, 2, True)
    yield "render · panel Configuración de escena", "render.PanelEscena", lambda: render.PanelEscena(v.area)
    yield "render · panel Aspecto", "render.PanelAspecto", lambda: render.PanelAspecto(s.doc, v.area)
    yield "boceto · Autorrestringir", "dialogo_autorestringir.DialogoAutoRestringir", \
        lambda: dialogo_autorestringir.DialogoAutoRestringir(boceto, {}, None, v)
    yield "malla · Guardar malla", "guardar_malla.DialogoGuardarMalla", \
        lambda: guardar_malla.DialogoGuardarMalla(malla or list(est.cuerpos.values()), (), None, v)
    yield "dibujo · Vista", "dibujo.DialogoVista", lambda: dibujo.DialogoVista(v, [(c.id, c.nombre) for c in est.cuerpos.values()], None)
    yield "animación · Acción", "animacion.DialogoAccion", lambda: animacion.DialogoAccion(v, "transformar", {"inicio": 0.0, "duracion": 1.0}, 2, True)
    yield "animación · Publicar", "animacion.DialogoPublicar", lambda: animacion.DialogoPublicar(v, (1280, 720), "x.mp4")
    yield "administrar · Roscas", "administrar.DialogoRoscas", lambda: administrar.DialogoRoscas(v)
    yield "administrar · Configuraciones", "administrar.DialogoConfiguraciones", lambda: administrar.DialogoConfiguraciones(s.doc, v)
    yield "administrar · Lista de materiales", "administrar.DialogoListaMateriales", \
        lambda: administrar.DialogoListaMateriales(s.doc, v)
    yield "administrar · Scripts", "administrar.DialogoScripts", lambda: administrar.DialogoScripts(v)
    yield "diseño · Parámetros", "dialogo_parametros.DialogoParametros", lambda: dialogo_parametros.DialogoParametros(s.doc, v)
    yield "diseño · Rejilla", "dialogos.DialogoRejilla", lambda: dialogos.DialogoRejilla(None, v)
    yield "aspecto · Editor de materiales", "aspectos_ui.EditorMateriales", lambda: aspectos_ui.EditorMateriales({}, v)
    yield "ajustes · Atajo", "mas_comando.DialogoAtajo", lambda: mas_comando.DialogoAtajo("Extruir", "E", "E", lambda _t: None, v)


def medir(nombre, clase, fabrica):
    d = fabrica()
    d.show()
    A.esperar(120)
    hint, minimo = d.sizeHint(), d.minimumSizeHint()
    scroll = d.findChildren(QScrollArea)
    botones = [b for b in d.findChildren(QAbstractButton) if b.isVisible() and b.text() in ("Aceptar", "Cancelar", "OK", "Cerrar", "Guardar")]
    fuera = [b.text() for b in botones if not d.rect().contains(b.mapTo(d, b.rect().center()))]
    fila = {"nombre": nombre, "clase": clase, "ancho": d.width(), "alto": d.height(), "hint": [hint.width(), hint.height()],
            "minimo": [minimo.width(), minimo.height()], "cabe_en_1280x720": hint.width() <= PANTALLA[0] and hint.height() <= PANTALLA[1],
            "con_desplazamiento": bool(scroll), "botones_fuera": fuera,
            "desborde_horizontal": any(sc.horizontalScrollBar().isVisible() for sc in scroll)}
    d.grab().save(str(CARPETA / (nombre.replace(" · ", "_").replace(" ", "_").replace("(", "").replace(")", "") + ".png")))
    d.close()
    d.deleteLater()
    return fila


filas = []
for nombre, clase, fab in fabricas():
    try:
        f = medir(nombre, clase, fab)
        ok = f["cabe_en_1280x720"] and not f["botones_fuera"] and not f["desborde_horizontal"]
        A.reg(AR, nombre, ok, json.dumps({k: x for k, x in f.items() if k not in ("nombre", "clase")}, ensure_ascii=False))
    except Exception as e:  # noqa: BLE001 — un diálogo que no se puede armar sin su contexto se anota, no corta el inventario
        f = {"nombre": nombre, "clase": clase, "abierto": False, "motivo": f"{type(e).__name__}: {e}"[:160]}
        A.reg(AR, nombre, False, f["motivo"])
    filas.append(f)
(CARPETA.parent / f"inventario_dialogos_{FASE}.json").write_text(json.dumps(filas, ensure_ascii=False, indent=1), encoding="utf-8")
A.reg(AR, "no se escapó ninguna excepción dentro de un slot de Qt", not A.ERRORES, "; ".join(A.ERRORES)[:300])
A.guardar_registro(f"dialogos_inventario_{FASE}")
fallas = sum(1 for r in A.REGISTRO if not r["ok"])
print(f"=== {len(A.REGISTRO)} comprobaciones, {fallas} con ✗", flush=True)
