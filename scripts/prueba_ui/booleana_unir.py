# -*- coding: utf-8 -*-
"""Editar una extrusión de «Cuerpo nuevo» a «Unir» en la ventana real, sobre una placa con agujeros B-spline, y medir
cuánto tarda: el panel de Extruir, la vista previa, Aceptar, el aviso «Calculando…» del timeline y deshacer.

Antes de la mejora (evidencias/booleanas_2026-10-26) esta edición tardaba segundos de más: el volumen con malla de
`aplicar_resultado`, el BRepCheck de todo el resultado y las cajas exactas de `se_tocan`."""
import sys
import tempfile
import time
from pathlib import Path

import arnes as A
from OCP.BRepTools import BRepTools

from omnicad import api
from omnicad.nucleo import geometria as geo

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from bench_booleana import _forma_base  # noqa: E402  (el mismo cuerpo base que el banco de medición)

AR = "BOOLEANA·UNIR"
AGUJEROS = 120
TOPE_S = 8.0            # con 120 agujeros B-spline: ~1 s hoy; antes ~4 s. Holgado a propósito (PC con poca memoria)

placa = _forma_base(AGUJEROS, "bspline")
brep = Path(tempfile.mkdtemp(prefix="omnicad_unir_")) / "placa.brep"
BRepTools.Write_s(placa, str(brep))
s = api.Sesion()


def llamar(herramienta, **a):
    r = api.llamar(s, herramienta, a)
    assert r["ok"], r
    return r["result"]


llamar("open_document", path=str(brep))
boceto = llamar("create_sketch", plane=">Z")["sketch"]["id"]
llamar("draw_rectangle", x1=100, y1=-10, x2=120, y2=10)
paso = llamar("extrude", sketch=boceto, profile=0, distance=5, operation="new_body")["feature"]["id"]
app, v = A.iniciar(s.doc)
A.reg(AR, "arranca con la extrusión como Cuerpo nuevo (2 cuerpos)", len(v.doc.estado_final.cuerpos) == 2,
      f"{len(v.doc.estado_final.cuerpos)} cuerpos")

# El aviso «Calculando…» tiene que estar PINTADO en el timeline mientras se calcula la vista previa (Aceptar la reusa).
vistos = []
original = v._calculando


def espiar(op):
    original(op)
    vistos.append(v.timeline.estado.text())


v._calculando = espiar
v.doc.al_calcular = espiar

A.MODALES.clear()
v.editar_operacion(paso)
A.esperar(300)
p = v.panel
A.reg(AR, "al editar la extrusión se abre el panel", p is not None and p.isVisible(), f"modales={A.MODALES}")
t = time.perf_counter()
p.set_valor("operacion", "unir")
p._t_previa.stop()
p._calcular_previa()
previa = time.perf_counter() - t
A.esperar(120)
st = A.estado_panel(p)
A.reg(AR, "vista previa de Unir", st["op"] and st["previa_ok"], f"{previa:.2f} s; mensaje=«{st['mensaje']}»")
A.reg(AR, f"la vista previa de Unir tarda menos de {TOPE_S:.0f} s", previa < TOPE_S, f"{previa:.2f} s")
A.reg(AR, "el timeline mostró «Calculando <paso>…» mientras calculaba la vista previa",
      any(x.startswith("Calculando") and "Extrusi" in x for x in vistos), f"{vistos[:3]}")
vistos.clear()
t = time.perf_counter()
p.aceptar()
aceptar = time.perf_counter() - t
A.esperar(450)
A.reg(AR, f"Aceptar (Cuerpo nuevo → Unir) tarda menos de {TOPE_S:.0f} s", aceptar < TOPE_S, f"{aceptar:.2f} s")
cuerpos = list(v.doc.estado_final.cuerpos.values())
A.reg(AR, "queda un solo cuerpo", len(cuerpos) == 1, f"{len(cuerpos)} cuerpos")
if len(cuerpos) == 1:
    forma = cuerpos[0].forma
    esperado = geo.volumen(placa) + 20 * 20 * 5
    obtenido = geo.volumen(forma)
    A.reg(AR, "el volumen es el de la placa más la extrusión", abs(obtenido - esperado) <= 1e-3 * esperado,
          f"obtenido {obtenido:.1f}, esperado {esperado:.1f}")
    A.reg(AR, "el sólido es válido y de una pieza", geo.es_valida(forma) and len(geo.solidos(forma)) == 1)

# Reabrir y volver a Cuerpo nuevo: tiene que ser instantáneo (sin booleana) y devolver los dos cuerpos.
v.editar_operacion(paso)
A.esperar(250)
p = v.panel
t = time.perf_counter()
p.set_valor("operacion", "nuevo")
p._t_previa.stop()
p._calcular_previa()
p.aceptar()
nuevo = time.perf_counter() - t
A.esperar(450)
A.reg(AR, "volver a Cuerpo nuevo deja los 2 cuerpos", len(v.doc.estado_final.cuerpos) == 2,
      f"{len(v.doc.estado_final.cuerpos)} cuerpos, {nuevo:.2f} s")
A.deshacer(v)
A.reg(AR, "deshacer vuelve a Unir (1 cuerpo)", len(v.doc.estado_final.cuerpos) == 1,
      f"{len(v.doc.estado_final.cuerpos)} cuerpos")
A.foto(v, "booleana_unir")

A.reg("GENERAL", "ninguna excepción escapó de un slot de Qt en toda la corrida", not A.ERRORES,
      f"{len(A.ERRORES)}: {A.ERRORES[:1]}")
A.guardar_registro("booleana_unir")
fallas = [r for r in A.REGISTRO if not r["ok"]]
print(f"\n=== {len(A.REGISTRO)} comprobaciones, {len(fallas)} con ✗ ===")
v.doc.modificado = False
v.close()
sys.exit(0)
