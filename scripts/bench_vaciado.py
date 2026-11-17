# -*- coding: utf-8 -*-
"""B-620: dónde se van los segundos de la previa de un Vaciado de 2 cuerpos (1 mm, cadena tangente).

Dos solevaciones regladas entre círculos corridos (caras B-spline de 2 polos, como una extrusión de spline de un .f3d),
entradas como Operación base (como abre un .f3d), y un Vaciado de 1 mm con cadena tangente que quita las dos tapas
(un empalme arriba hace fallar al kernel con 1 mm en estas solevaciones). Mide: el paso en la ventana, la previa aparte (1.ª abre el trabajador, 2.ª reusa) y
aceptar aparte; y, dentro de la previa, sus etapas en este proceso (rehacer el documento, kernel, mallar, codificar) y
la revisión de cruces de los cuerpos vaciados como la hace el trabajador.

Uso (desde `clon/`):  .venv/bin/python ../scripts/bench_vaciado.py [--deflexion 0.05]
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


def _solevacion_reglada(x):
    from OCP.BRepBuilderAPI import BRepBuilderAPI_MakeEdge, BRepBuilderAPI_MakeWire
    from OCP.BRepOffsetAPI import BRepOffsetAPI_ThruSections
    from OCP.gp import gp_Ax2, gp_Circ, gp_Dir, gp_Pnt

    from omnicad.nucleo import geometria as geo

    s = BRepOffsetAPI_ThruSections(True, True)
    for cx, cy, z, r in ((x, 0, 0, 30), (x + 8, 3, 40, 20)):
        circ = gp_Circ(gp_Ax2(gp_Pnt(cx, cy, z), gp_Dir(0, 0, 1)), r)
        s.AddWire(BRepBuilderAPI_MakeWire(BRepBuilderAPI_MakeEdge(circ).Edge()).Wire())
    s.Build()
    return geo.solidos(s.Shape())[0]


def main():
    import numpy as np

    from omnicad.nucleo import aislado, intercambio, revision
    from omnicad.nucleo import referencias as refs
    from omnicad.timeline import calculo_aislado as ca
    from omnicad.timeline.documento import Documento
    from omnicad.timeline.operaciones import OpOperacionBase
    from omnicad.timeline.ops_modificar import OpVaciado

    a = argparse.ArgumentParser()
    a.add_argument("--deflexion", type=float, default=None, help="la del visor; sin dar: «Automático»")
    deflexion = a.parse_args().deflexion

    breps = [intercambio.brep_a_texto(_solevacion_reglada(x)) for x in (0, 100)]

    def doc_cuerpos():
        doc = Documento()
        _exigir(doc.agregar(OpOperacionBase(doc.nuevo_id(), cuerpos=[{"id": f"c{i}", "nombre": f"Cuerpo{i}",
                                                                      "brep": b} for i, b in enumerate(breps)])))
        return doc

    def op(doc):
        caras = []
        for cid, c in doc.estado_final.cuerpos.items():
            caras += [refs.referencia(cid, s, c.forma) for s in refs.subformas(c.forma, "cara")
                      if np.isclose(refs.firma(s)["centro"][2], 40)]
        return OpVaciado(doc.nuevo_id(), "Vaciado1", caras=caras, espesor_interior="1 mm", tangente=True)

    def datos(d, o):
        return {"receta": d.a_dict(), "operacion": o.a_dict(), "indice": None, "deflexion": deflexion, "angular": 0.5,
                "formas": True}

    filas = []
    aislado.cerrar_trabajador()
    doc = doc_cuerpos()
    o = op(doc)
    filas.append(("paso en la ventana", *_reloj(lambda: _exigir((d := doc_cuerpos()).agregar(op(d))))))
    filas.append(("previa aparte (1.ª: abre el trabajador)", *_reloj(lambda: aislado.correr_json("previa_visual", datos(doc, o), 60))))
    filas.append(("previa aparte (2.ª)", *_reloj(lambda: aislado.correr_json("previa_visual", datos(doc, o), 60))))
    filas.append(("aceptar aparte", *_reloj(lambda: _exigir(doc.agregar(op(doc), aparte=True)))))
    aislado.cerrar_trabajador()

    # Etapas de `previa_visual` en este proceso (las mismas llamadas, una a una)
    doc = doc_cuerpos()
    o = op(doc)
    receta, d, cids = doc.a_dict(), {}, list(doc.estado_final.cuerpos)
    filas.append(("· rehacer el documento", *_reloj(lambda: d.update(doc=Documento.desde_dict(receta)))))
    filas.append(("· kernel (previsualizar)", *_reloj(lambda: d.update(e=d["doc"].previsualizar(o, None, en_vivo=True)[0]))))
    filas.append(("· mallar 2 cuerpos", *_reloj(lambda: d.update(m={c: ca._malla(d["e"].cuerpos[c].forma, deflexion, 0.5)
                                                                   for c in cids}))))
    filas.append(("· codificar", *_reloj(lambda: ca._codificar({"mallas": d["m"], "formas": {c: d["e"].cuerpos[c].forma for c in cids}},
                                                               transporte=False))))
    aislado.EN_HIJO = True      # la revisión de cruces del vaciado (`_exigir_pared_sin_cruces`) como corre en el trabajador
    filas.append(("· cruces de los 2 vaciados, en el trabajador", *_reloj(lambda: [
        revision._autointersecciones_seguras(d["e"].cuerpos[c].forma, 1, 5.0) for c in cids])))
    aislado.EN_HIJO = False
    print(f"| etapa (deflexión {deflexion or 'automática'}) | s | resultado |\n|---|---|---|")
    for etapa, s, res in filas:
        print(f"| {etapa} | {s:.3f} | {res} |")


def _exigir(res):
    if res.estado != "ok":
        raise RuntimeError(res.mensaje)


if __name__ == "__main__":
    main()
