# -*- coding: utf-8 -*-
"""P-43: costo de adoptar un cálculo aislado (cambio de parámetros en un documento de 71 pasos) en el visor.

Un documento de 71 cajas independientes donde solo la última usa el parámetro `altura`. Se cambia el parámetro: el
cálculo completo vuelve de un proceso aparte y se adopta. Mide cuánto tarda la adopción, cuánto la primera
`set_modelo` posterior y cuántos cuerpos se vuelven a teselar (los 70 intactos no deberían).

Uso, desde `clon/`:
    .venv/Scripts/python.exe ../scripts/turno.py -- .venv/Scripts/python.exe ../scripts/medir_adopcion.py [etiqueta]
Deja `evidencias/adopcion_<etiqueta>.json`.
"""
import json
import sys
import time
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ / "clon"))

from omnicad.nucleo import aislado, motor  # noqa: E402
from omnicad.timeline.documento import Documento  # noqa: E402
from omnicad.timeline.operaciones import OpPrimitiva  # noqa: E402
from omnicad.timeline.parametros import TablaParametros  # noqa: E402
from omnicad.ui import visor3d as vis  # noqa: E402
from PySide6.QtWidgets import QApplication  # noqa: E402


def main():
    etiqueta = sys.argv[1] if len(sys.argv) > 1 else "medida"
    app = QApplication.instance() or QApplication([])
    out = {"etiqueta": etiqueta}
    with motor.fijar_motor("opencascade"):
        umbral, aislado.UMBRAL_PREVUELO_PARAMETROS = aislado.UMBRAL_PREVUELO_PARAMETROS, 10 ** 6   # armar sin hijos
        d = Documento()
        d.parametros.agregar("altura", "3 mm")
        for i in range(70):
            d.agregar(OpPrimitiva(d.nuevo_id(), forma="caja", ancho="10", largo="10", alto="10", x=str(i * 12)))
        d.agregar(OpPrimitiva(d.nuevo_id(), forma="caja", ancho="10", largo="10", alto="altura", x="900"))
        aislado.UMBRAL_PREVUELO_PARAMETROS = umbral
        out["pasos"] = len(d.operaciones)
        visor = vis.Visor3D()
        visor.resize(800, 600)
        visor.set_modelo(d.estado_final)                       # el visor ya mostraba el modelo
        viejas = {cid: c.forma for cid, c in d.estado_final.cuerpos.items()}
        tabla = TablaParametros.desde_lista(d.parametros.a_lista())
        tabla.modificar("altura", "7 mm")
        tiempos = {}
        original = Documento._aplicar_calculo

        def medir_adopcion(self, calculo):
            inicio = time.perf_counter()
            original(self, calculo)
            tiempos["adopcion_ms"] = (time.perf_counter() - inicio) * 1000

        Documento._aplicar_calculo = medir_adopcion
        inicio = time.perf_counter()
        d.aplicar_parametros(tabla)                              # cálculo en un proceso aparte + adopción
        out["aplicar_parametros_total_ms"] = round((time.perf_counter() - inicio) * 1000, 1)
        out["adopcion_ms"] = round(tiempos["adopcion_ms"], 1)
        llamadas = []
        teselar = vis.teselar_cuerpo

        def contar(forma, *a, **k):
            llamadas.append(forma)
            return teselar(forma, *a, **k)

        vis.teselar_cuerpo = contar
        inicio = time.perf_counter()
        visor.set_modelo(d.estado_final)
        out["primera_set_modelo_ms"] = round((time.perf_counter() - inicio) * 1000, 1)
        out["teselados"] = len(llamadas)
        nuevas = {cid: c.forma for cid, c in d.estado_final.cuerpos.items()}
        out["cuerpos"] = len(nuevas)
        out["formas_conservadas"] = sum(nuevas[c] is viejas[c] for c in nuevas)
        visor.close()
    ruta = RAIZ / "evidencias" / f"adopcion_{etiqueta}.json"
    ruta.write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")
    print(json.dumps(out, ensure_ascii=False, indent=1))
    del app


main()
