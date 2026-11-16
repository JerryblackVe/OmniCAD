# -*- coding: utf-8 -*-
"""B-608: dónde se van los segundos de un Empalme (o Chaflán) en 4 aristas de una caja simple.

Arma una caja de 143×106×40 (1 cuerpo) y mide por etapa: el kernel solo (`solidos_modificar.empalme`), el paso en la
ventana (`Documento.agregar`), la previa en el proceso aparte (la 1.ª abre el trabajador) y el paso
aceptado aparte (`agregar(aparte=True)`), con un radio que entra (5) y otro que no (50).

Uso (desde `clon/`):  .venv/bin/python ../scripts/bench_empalme.py [--chaflan]
"""
import argparse
import os
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "clon"))
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")


def _reloj(fn):
    t = time.perf_counter()
    try:
        fn()
        res = "ok"
    except Exception as e:  # noqa: BLE001 — se informa el mensaje
        res = str(e).splitlines()[0][:60]
    return time.perf_counter() - t, res


def main():
    import numpy as np

    from omnicad.nucleo import aislado
    from omnicad.nucleo import referencias as refs
    from omnicad.timeline.documento import Documento
    from omnicad.timeline.operaciones import OpPrimitiva
    from omnicad.timeline.ops_modificar import OpChaflan, OpEmpalme

    a = argparse.ArgumentParser()
    a.add_argument("--chaflan", action="store_true")
    chaflan = a.parse_args().chaflan

    def doc_caja():
        doc = Documento()
        doc.agregar(OpPrimitiva(doc.nuevo_id(), forma="caja", ancho="143 mm", largo="106 mm", alto="40 mm"))
        return doc

    def op(doc, r):
        forma = doc.estado_final.cuerpos["op1.c1"].forma
        aristas = [refs.referencia("op1.c1", s, forma) for s in refs.subformas(forma, "arista")
                   if np.isclose(refs.firma(s)["medio"][2], 40)]
        if chaflan:
            return OpChaflan(doc.nuevo_id(), "Chaflán1", aristas=aristas, distancia=f"{r} mm")
        return OpEmpalme(doc.nuevo_id(), "Empalme1", aristas=aristas, radio=f"{r} mm")

    def previa(doc, o):
        return aislado.correr_json("previa_visual", {"receta": doc.a_dict(), "operacion": o.a_dict(), "indice": 1,
                                                     "deflexion": 0.05, "angular": 0.5, "formas": True}, 30)

    filas = []
    for r in (5, 50):
        aislado.cerrar_trabajador()
        doc = doc_caja()
        filas.append((r, "paso en la ventana", *_reloj(lambda d=doc, r=r: _exigir(d.agregar(op(d, r))))))
        doc = doc_caja()
        o = op(doc, r)
        filas.append((r, "previa aparte (1.ª: abre el trabajador)", *_reloj(lambda d=doc, o=o: previa(d, o))))
        filas.append((r, "previa aparte (2.ª)", *_reloj(lambda d=doc, o=o: previa(d, o))))
        filas.append((r, "aceptar aparte", *_reloj(lambda d=doc, r=r: _exigir(d.agregar(op(d, r), aparte=True)))))
    aislado.cerrar_trabajador()
    print(f"| radio | etapa ({'chaflán' if chaflan else 'empalme'}) | s | resultado |\n|---|---|---|---|")
    for r, etapa, s, res in filas:
        print(f"| {r} | {etapa} | {s:.3f} | {res} |")


def _exigir(res):
    if res.estado != "ok":
        raise RuntimeError(res.mensaje)


if __name__ == "__main__":
    main()
