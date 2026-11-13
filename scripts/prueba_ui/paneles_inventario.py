# -*- coding: utf-8 -*-
"""Inventario de paneles de comando: abre CADA comando de CATALOGO en la ventana real (1280x720 por defecto), mide su
panel (tamaño, campos, barra, desborde horizontal, si entra en el lienzo) y guarda una captura del panel.
    paneles_inventario.py [fase] [ancho alto]      fase = «antes» o «despues» (carpeta de capturas), por defecto «despues».
Deja `evidencias/ui_paneles_2026-10-31/<fase>/*.png` y `inventario_<fase>.json` (para la matriz de cobertura).
Eventos simulados al widget; no usa el cursor real."""
import json
import sys

import arnes as A
import escena
from omnicad import api
from omnicad.ui.comandos import CATALOGO

FASE = sys.argv[1] if len(sys.argv) > 1 else "despues"
ANCHO, ALTO = (int(sys.argv[2]), int(sys.argv[3])) if len(sys.argv) > 3 else (1280, 720)
AR = f"PANELES·{FASE}·{ANCHO}x{ALTO}"
CARPETA = A.SALIDA.parent / "ui_paneles_2026-10-31" / FASE
CARPETA.mkdir(parents=True, exist_ok=True)

s, ids = escena.construir()


def ampliar(nombre, **args):
    """Suma a la escena lo que piden los comandos de malla, chapa plegada y ensamble (un paso que falla no corta)."""
    r = api.llamar(s, nombre, args)
    if not r["ok"]:
        print(f"[escena] {nombre} no se pudo: {str(r)[:160]}", flush=True)
    return r


ampliar("create_box", length=20, width=20, height=20, x=-300)
ampliar("tessellate", bodies=ids["caja"], refinement="low", keep_original=True)
ampliar("create_sketch", name="Chapa", plane="XY")
ampliar("draw_rectangle", sketch="Chapa", x1=300, y1=0, x2=340, y2=30)
chapa = ampliar("create_base_flange", sketch="Chapa")
if chapa["ok"]:
    ampliar("create_edge_flange", body=chapa["result"]["bodies_created"][0]["id"], edges=">Y and >Z", height=15)
ampliar("create_sketch", name="Trabajo", plane="XY")          # los comandos de boceto exigen un boceto abierto (B-382)
ampliar("draw_line", sketch="Trabajo", start_x=2, start_y=3, end_x=8, end_y=3)
ampliar("create_component", bodies=[ids["cil"]], name="CompA")
ampliar("create_component", bodies=[ids["caja"]], name="CompB")
for tipo in ("revolute", "slider"):
    ampliar("create_joint", origin1=">Z", body1="CompA", origin2=">Z", body2="CompB", joint_type=tipo)
app, v = A.iniciar(s.doc, ANCHO, ALTO)
A.esperar(300)
filas = []


EN_BOCETO = {"sk_curva_interseccion", "sk_proyectar_superficie"}       # los que dicen «Abrí un boceto para usar este comando»


def medir(clave):
    if v.panel is not None:
        v.panel.cancelar()
        A.esperar(60)
    if clave in EN_BOCETO and not v.modo_boceto.activo:       # como la persona: doble clic en el boceto del timeline
        v.editar_operacion(s.paso("Trabajo").id)
        A.esperar(400)
    elif clave not in EN_BOCETO and v.modo_boceto.activo:
        v.modo_boceto.terminar()
        A.esperar(200)
    comando = CATALOGO[clave]()
    modales = len(A.MODALES)
    panel = v.ejecutar_comando(comando)
    A.esperar(120)
    if panel is None or v.panel is None:
        motivo = A.MODALES[-1][1] if len(A.MODALES) > modales else "no abre"
        return {"clave": clave, "abierto": False, "motivo": motivo[:140]}
    area, cuerpo = v.area, panel.desplazador.widget()
    barra_v = panel.desplazador.verticalScrollBar().maximum() > 0
    ancho_cuerpo, ancho_vista = cuerpo.sizeHint().width(), panel.desplazador.viewport().width()
    titulo = panel.findChild(type(panel.mensaje), "titulo_comando")
    fila = {
        "clave": clave, "abierto": True, "tipo_panel": type(panel).__name__, "titulo": titulo.text() if titulo else "",
        "ancho": panel.width(), "alto": panel.height(), "campos": len(panel.campos),
        "visibles": sum(1 for c in panel.campos if panel._visible(c)), "barra_vertical": barra_v,
        "desborde_horizontal": ancho_cuerpo > ancho_vista + 1,
        "dentro_del_lienzo": area.rect().adjusted(0, 0, 1, 1).contains(panel.geometry()),
        "alto_natural_cuerpo": cuerpo.sizeHint().height(),
    }
    panel.grab().save(str(CARPETA / f"{clave}.png"))
    return fila


def todos():
    for clave in sorted(CATALOGO):
        try:
            f = medir(clave)
        except Exception as e:  # noqa: BLE001 — un comando que no abre se anota, no corta el inventario
            f = {"clave": clave, "abierto": False, "motivo": f"EXCEPCIÓN {type(e).__name__}: {e}"[:200]}
        filas.append(f)
        A.reg(AR, clave, f.get("abierto", False) and f.get("dentro_del_lienzo", False) and not f.get("desborde_horizontal", False),
              json.dumps({k: x for k, x in f.items() if k not in ("clave",)}, ensure_ascii=False)[:260])
    if v.panel is not None:
        v.panel.cancelar()


A.correr(AR, todos)
(CARPETA.parent / f"inventario_{FASE}.json").write_text(json.dumps(filas, ensure_ascii=False, indent=1), encoding="utf-8")
A.reg(AR, "no se escapó ninguna excepción dentro de un slot de Qt", not A.ERRORES, "; ".join(A.ERRORES)[:300])
A.guardar_registro(f"paneles_inventario_{FASE}")
fallas = sum(1 for r in A.REGISTRO if not r["ok"])
print(f"=== {len(A.REGISTRO)} comprobaciones, {fallas} con ✗", flush=True)
