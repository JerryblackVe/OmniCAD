# -*- coding: utf-8 -*-
"""Base de rendimiento para decidir (y comprobar) qué pasa a Rust: mide el solver de bocetos, las operaciones de malla
y el recálculo de un proyecto. Solo lectura: no escribe archivos.

Uso (desde `clon/`, con turno porque abre OpenCascade y arma mallas grandes):
    .venv/Scripts/python.exe ../scripts/turno.py -- .venv/Scripts/python.exe ../scripts/bench_rendimiento.py solver
    .venv/Scripts/python.exe ../scripts/turno.py -- .venv/Scripts/python.exe ../scripts/bench_rendimiento.py malla
    .venv/Scripts/python.exe ../scripts/turno.py -- .venv/Scripts/python.exe ../scripts/bench_rendimiento.py recalculo ../motor_cohete.omnicad
    .venv/Scripts/python.exe ../scripts/turno.py -- .venv/Scripts/python.exe ../scripts/bench_rendimiento.py frontera

Se corre antes y después de cada paso de `docs/plan_rust.md` y los números van al PROJECT_LOG.
La primera medida del solver incluye el import de scipy (se imprime aparte, a propósito).
"""
import math
import sys
import time
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ / "clon"))


def _ms(t0):
    return (time.perf_counter() - t0) * 1000.0


def solver():
    from omnicad.restricciones import Boceto, resolver

    def rectangulos(n):
        b, vals = Boceto(), {}
        for k in range(n):
            ls = b.agregar_rectangulo((k * 40, 0), (k * 40 + 30, 20))
            b.agregar_restriccion("fijo", [b.curvas[ls[0]].p1])
            vals[b.agregar_cota("distancia", [ls[0]], "30")] = 30
            vals[b.agregar_cota("distancia", [ls[1]], "20")] = 20
        return b, vals

    def poligono(n):
        b, vals = Boceto(), {}
        pts = [(math.cos(2 * math.pi * i / n) * 50, math.sin(2 * math.pi * i / n) * 50) for i in range(n)]
        ls = [b.agregar_linea(pts[i], pts[(i + 1) % n]) for i in range(n)]
        for i in range(n):
            b.agregar_restriccion("coincidente", [b.curvas[ls[i]].p2, b.curvas[ls[(i + 1) % n]].p1])
        b.agregar_restriccion("fijo", [b.curvas[ls[0]].p1])
        for i in range(n):
            vals[b.agregar_cota("distancia", [ls[i]], "20")] = 20
        return b, vals

    b, v = rectangulos(1)
    t = time.perf_counter()
    resolver(b, v)
    print(f"primer resolver (incluye import de scipy)  {_ms(t):8.1f} ms")
    for nombre, fn, tamanos in (("rectángulos", rectangulos, (5, 20, 60)), ("polígono", poligono, (6, 12, 24))):
        for n in tamanos:
            b, v = fn(n)
            t = time.perf_counter()
            r = resolver(b, v)
            print(f"{nombre:12s} n={n:3d}  puntos={len(b.puntos):4d}  resolver {_ms(t):8.1f} ms  ok={r.ok}")
    b, v = poligono(24)
    resolver(b, v)
    pid = next(iter(b.puntos))
    t = time.perf_counter()
    for _ in range(10):
        b.puntos[pid].x += 0.5
        resolver(b, v, arrastrado=pid)
    print(f"arrastre polígono 24: {_ms(t) / 10:.1f} ms por evento de ratón (el cuadro de 60 Hz da 16 ms)")


def malla():
    from OCP.BRepPrimAPI import BRepPrimAPI_MakeSphere

    from omnicad.nucleo import malla as M

    esfera = BRepPrimAPI_MakeSphere(20.0).Shape()
    for etiqueta, desviacion in (("~10k triángulos", 0.02), ("~50k triángulos", 0.004)):
        t = time.perf_counter()
        m = M.desde_brep(esfera, desviacion=desviacion)
        print(f"--- {etiqueta} ({len(m.caras)} caras)   desde_brep {_ms(t):.0f} ms")
        for nombre, fn in (("analizar", lambda m=m: M.analizar(m)),
                           ("suavizar 10 it", lambda m=m: M.suavizar(m, iteraciones=10)),
                           ("reducir 50 %", lambda m=m: M.reducir(m, proporcion=0.5)),
                           ("reparar", lambda m=m: M.reparar(m)),
                           ("remallar", lambda m=m: M.remallar(m, densidad=0.5)),
                           ("cortar_plano", lambda m=m: M.cortar_plano(m, (0, 0, 0), (0, 0, 1)))):
            t = time.perf_counter()
            fn()
            print(f"  {nombre:16s} {_ms(t):9.1f} ms")


def recalculo(ruta):
    from omnicad.io_archivos import proyecto
    from omnicad.nucleo import geometria as geo

    t = time.perf_counter()
    doc = proyecto.abrir(ruta)
    print(f"abrir                {_ms(t):8.0f} ms   pasos={len(doc.operaciones)}")
    t = time.perf_counter()
    doc.recalcular(0)
    print(f"recalcular todo      {_ms(t):8.0f} ms")
    lentos = sorted(zip(doc._duraciones, [o.TIPO for o in doc.operaciones], strict=True), reverse=True)[:5]
    print("pasos más lentos:    " + ", ".join(f"{tipo} {d * 1000:.0f} ms" for d, tipo in lentos))
    formas = [c.forma for c in doc.estado_final.cuerpos.values() if getattr(c, "forma", None) is not None]
    t = time.perf_counter()
    triangulos = sum(len(geo.teselar(f, rehacer=True)[0]) // 3 for f in formas)
    print(f"teselar {len(formas)} cuerpos  {_ms(t):8.0f} ms   {triangulos} triángulos")


def frontera():
    """La frontera Python↔OpenCascade: GIL, extracción de una triangulación e iteración de colecciones de OCP."""
    import itertools
    import threading

    from OCP.BRep import BRep_Tool
    from OCP.BRepBuilderAPI import BRepBuilderAPI_Copy
    from OCP.BRepMesh import BRepMesh_IncrementalMesh
    from OCP.BRepPrimAPI import BRepPrimAPI_MakeBox, BRepPrimAPI_MakeSphere
    from OCP.OCP.collections import IndexedDataMap_TopoDS_Shape_List_TopoDS_Shape_TopTools_ShapeMapHasher as Mapa
    from OCP.TopAbs import TopAbs_EDGE, TopAbs_FACE
    from OCP.TopExp import TopExp
    from OCP.TopLoc import TopLoc_Location

    from omnicad.nucleo import geometria as geo

    # 1) ¿OCP suelta el GIL? Dos esferas mallando en dos hilos contra en serie (sin paralelo interno de OCC).
    def fresca():
        return BRepBuilderAPI_Copy(BRepPrimAPI_MakeSphere(20.0).Shape(), True).Shape()

    def mallar(forma):
        BRepMesh_IncrementalMesh(forma, 0.003, False, 0.1, False)

    a, b = fresca(), fresca()
    t = time.perf_counter()
    mallar(a)
    mallar(b)
    serie = _ms(t)
    a, b = fresca(), fresca()
    hilos = [threading.Thread(target=mallar, args=(x,)) for x in (a, b)]
    t = time.perf_counter()
    for h in hilos:
        h.start()
    for h in hilos:
        h.join()
    par = _ms(t)
    print(f"GIL: serie {serie:.0f} ms, 2 hilos {par:.0f} ms -> {'SUELTA' if par < serie * 0.75 else 'RETIENE'} el GIL")

    # 2) Extraer la triangulación nodo a nodo (lo que hace teselar_por_cara) contra el costo de mallar.
    esfera = BRepPrimAPI_MakeSphere(20.0).Shape()
    t = time.perf_counter()
    BRepMesh_IncrementalMesh(esfera, 0.002, False, 0.1, True)
    t_malla = _ms(t)
    t = time.perf_counter()
    n = sum(len(tr) for _, tr in geo.teselar_por_cara(esfera))
    t_total = _ms(t)
    print(f"malla {t_malla:.0f} ms | teselar_por_cara (con malla ya hecha) {t_total:.0f} ms para {n} triángulos "
          f"= {t_total * 1000 / max(n, 1):.1f} µs por triángulo")
    tri = BRep_Tool.Triangulation_s(next(iter(geo.caras(esfera))), TopLoc_Location())
    t = time.perf_counter()
    for i in range(1, 100001):
        tri.Node(1 + i % tri.NbNodes())
    print(f"100000 llamadas tri.Node(i): {_ms(t):.0f} ms (~{_ms(t) / 100:.2f} µs por llamada)")

    # 3) Iterar una colección de OCP con `for` contra islice(Size()).
    mapa = Mapa()
    TopExp.MapShapesAndAncestors_s(BRepPrimAPI_MakeBox(10, 10, 10).Shape(), TopAbs_EDGE, TopAbs_FACE, mapa)
    lista = mapa.FindFromIndex(1)
    for etiqueta, fn in (("for x in lista", lambda: [x for x in lista]),
                         ("islice(lista, Size())", lambda: list(itertools.islice(lista, lista.Size())))):
        fn()
        t = time.perf_counter()
        for _ in range(200):
            fn()
        print(f"{etiqueta:24s} {_ms(t) / 200 * 1000:8.1f} µs por recorrido")


if __name__ == "__main__":
    modo = sys.argv[1] if len(sys.argv) > 1 else ""
    if modo == "solver":
        solver()
    elif modo == "malla":
        malla()
    elif modo == "frontera":
        frontera()
    elif modo == "recalculo" and len(sys.argv) > 2:
        recalculo(sys.argv[2])
    else:
        sys.exit(__doc__)
