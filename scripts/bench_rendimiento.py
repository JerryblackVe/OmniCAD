# -*- coding: utf-8 -*-
"""Base de rendimiento para decidir (y comprobar) qué pasa a Rust: mide el solver de bocetos, las operaciones de malla
y el recálculo de un proyecto. Solo lectura: no escribe archivos.

Uso (desde `clon/`, con turno porque abre OpenCascade y arma mallas grandes):
    .venv/Scripts/python.exe ../scripts/turno.py -- .venv/Scripts/python.exe ../scripts/bench_rendimiento.py solver
    .venv/Scripts/python.exe ../scripts/turno.py -- .venv/Scripts/python.exe ../scripts/bench_rendimiento.py malla
    .venv/Scripts/python.exe ../scripts/turno.py -- .venv/Scripts/python.exe ../scripts/bench_rendimiento.py recalculo ../motor_cohete.omnicad
    .venv/Scripts/python.exe ../scripts/turno.py -- .venv/Scripts/python.exe ../scripts/bench_rendimiento.py frontera
    .venv/Scripts/python.exe ../scripts/turno.py -- .venv/Scripts/python.exe ../scripts/bench_rendimiento.py memoria
    .venv/Scripts/python.exe ../scripts/turno.py -- .venv/Scripts/python.exe ../scripts/bench_rendimiento.py interfaz

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
    previo = resolver(b, v)
    t = time.perf_counter()
    for _ in range(10):
        b.puntos[pid].x += 0.5
        resolver(b, v, arrastrado=pid, previo=previo)
    print(f"arrastre polígono 24 en el editor (con `previo`): {_ms(t) / 10:.1f} ms por evento de ratón")


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
    doc.olvidar_memoria()          # «todo» de verdad: sin la memoria por paso que dejó abrir
    t = time.perf_counter()
    doc.recalcular(0)
    print(f"recalcular todo      {_ms(t):8.0f} ms")
    lentos = sorted(zip(doc._duraciones, [o.TIPO for o in doc.operaciones], strict=True), reverse=True)[:5]
    print("pasos más lentos:    " + ", ".join(f"{tipo} {d * 1000:.0f} ms" for d, tipo in lentos))
    # Editar un paso (misma receta, objeto nuevo: se recalcula él y lo que depende de su resultado).
    from omnicad.timeline.operaciones import operacion_desde_dict
    for k in (len(doc.operaciones) // 4, len(doc.operaciones) // 2):
        op = doc.operaciones[k]
        tiempos = []
        for olvidar in (True, False):
            if olvidar:
                doc.olvidar_memoria()
            t = time.perf_counter()
            doc.reemplazar(op.id, operacion_desde_dict(op.a_dict()))
            tiempos.append(_ms(t))
        print(f"editar el paso {k + 1:2d} ({op.TIPO}): sin memoria {tiempos[0]:6.0f} ms, con memoria {tiempos[1]:6.0f} ms")
    formas = [c.forma for c in doc.estado_final.cuerpos.values() if getattr(c, "forma", None) is not None]
    t = time.perf_counter()
    triangulos = sum(len(geo.teselar(f, rehacer=True)[0]) // 3 for f in formas)
    print(f"teselar {len(formas)} cuerpos  {_ms(t):8.0f} ms   {triangulos} triángulos")


def memoria():
    """P7: editar un paso del que no depende el resto (un cilindro aparte, antes de una placa con 4 roscas M3
    modeladas: el caso de 30 s de 34 del PROJECT_LOG). Sin memoria se recalcula todo lo posterior."""
    from omnicad import api

    sesion = api.Sesion()

    def llamar(nombre, **argumentos):
        r = api.llamar(sesion, nombre, argumentos)
        assert r["ok"], r
        return r["result"]

    llamar("create_cylinder", height=10, radius=4, x=40, name="Aparte")
    llamar("create_box", length=30, width=30, height=5, name="Placa")
    puntos = [[x, y, 5] for x, y in ((-8, -8), (-8, 8), (8, -8), (8, 8))]
    t = time.perf_counter()
    llamar("create_hole", body="Placa", face=">Z", points=puntos, hole_tap="modeled", thread="M3", depth=5)
    print(f"crear 4 roscas M3          {_ms(t):8.0f} ms")
    doc = sesion.doc
    for radio, olvidar in ((5, True), (6, False)):
        if olvidar:
            doc.olvidar_memoria()
        t = time.perf_counter()
        llamar("edit_feature", feature=doc.operaciones[0].id, params={"radius": radio})
        etiqueta = "sin memoria (como antes)" if olvidar else "con memoria por paso"
        print(f"editar el cilindro, {etiqueta:25s} {_ms(t):8.0f} ms   pasos={len(doc.operaciones)}")


def interfaz():
    """P3, P4, P5, P11 y P12 de docs/plan_rust.md: lo que corre en cada evento del ratón o al exportar, como era antes
    (reproducido acá) y como es ahora, en la misma corrida."""
    import os
    import struct
    from types import SimpleNamespace

    import numpy as np
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    from OCP.BRepPrimAPI import BRepPrimAPI_MakeSphere
    from PySide6.QtGui import QImage, QPainter, QPainterPath
    from PySide6.QtWidgets import QApplication

    from omnicad.nucleo import geometria as geo
    from omnicad.nucleo import malla as M
    from omnicad.ui.editor_boceto import Lienzo
    from omnicad.ui.visor3d import Visor3D, perspectiva, rayo_caja, rayo_triangulos

    app = QApplication.instance() or QApplication([])   # noqa: F841 — QPainter lo necesita
    vista = np.identity(4)
    vista[2, 3] = -300.0
    mvp = perspectiva(45, 1.5, 1, 2000) @ vista
    visor = SimpleNamespace(width=lambda: 1200, height=lambda: 800)
    visor.proyectar = lambda p, m: Visor3D.proyectar(visor, p, m)
    visor._a_pantalla = lambda p, m: Visor3D._a_pantalla(visor, p, m)
    plano = geo.Plano("XY")

    # P3: repintar 10 000 puntos de boceto (100 curvas de 100 puntos) en la vista 3D. La proyección (lo que hace
    # Python) y el dibujo antialiasado de Qt se miden por separado; la cámara quieta reusa lo proyectado.
    lienzo = SimpleNamespace(visor=visor, plano=plano, _mvp=mvp, _camara=lambda: None)
    lienzo.a_px = lambda x, y: Lienzo.a_px(lienzo, x, y)
    curvas = [tuple((math.cos(t) * (10 + k), math.sin(t) * (10 + k)) for t in np.linspace(0, 6.28, 100))
              for k in range(100)]
    for etiqueta, proyectar in (("antes", lambda c: [lienzo.a_px(*p) for p in c]),
                                ("ahora, 1er cuadro", lambda c: Lienzo._poli_px(lienzo, c)),
                                ("ahora, cámara quieta", lambda c: Lienzo._poli_px(lienzo, c))):
        t = time.perf_counter()
        polis = [proyectar(c) for c in curvas]
        print(f"P3 proyectar 10 000 puntos de boceto, {etiqueta}: {_ms(t):6.2f} ms")
    imagen = QImage(1200, 800, QImage.Format_ARGB32)
    p = QPainter(imagen)
    p.setRenderHint(QPainter.Antialiasing)
    t = time.perf_counter()
    for poli in polis:
        camino = QPainterPath(poli[0])
        for q in poli[1:]:
            camino.lineTo(q)
        p.drawPath(camino)
    print(f"P3 dibujar (Qt) con QPainterPath, antes: {_ms(t):6.1f} ms")
    t = time.perf_counter()
    for poli in polis:
        p.drawPolyline(poli)
    print(f"P3 dibujar (Qt) con drawPolyline, ahora: {_ms(t):6.1f} ms")
    p.end()

    # P4: cursor contra 1000 aristas (polilíneas de 12 puntos): una por una (antes) o en un paquete (ahora).
    rng = np.random.default_rng(0)
    polis = [np.cumsum(rng.normal(size=(12, 3)), axis=0) + rng.uniform(-80, 80, 3) for _ in range(1000)]
    q = np.array([600.0, 400.0])
    t = time.perf_counter()
    for poli in polis:
        Visor3D._dist_polilinea(visor, q, poli, mvp)
    print(f"P4 hover de 1000 aristas, antes: {_ms(t):6.1f} ms")
    paquete = Visor3D._empaquetar(polis)
    t = time.perf_counter()
    Visor3D._distancias_paquete(visor, paquete, q, mvp)
    print(f"P4 hover de 1000 aristas, ahora: {_ms(t):6.1f} ms (paquete armado una vez por forma)")

    # P5: rayo contra 20 cuerpos de 20 000 triángulos (400 k): todos (antes) o descartando por caja (ahora).
    cuerpos = [rng.uniform(-5, 5, (20000, 3, 3)) + np.array([k * 30.0, 0, 0]) for k in range(20)]
    cajas = [(c.reshape(-1, 3).min(0), c.reshape(-1, 3).max(0)) for c in cuerpos]
    o, d = np.array([0.0, 0.0, 100.0]), np.array([0.0, 0.0, -1.0])
    t = time.perf_counter()
    for c in cuerpos:
        rayo_triangulos(o, d, c)
    print(f"P5 rayo contra 400 k triángulos, antes: {_ms(t):6.1f} ms")
    t = time.perf_counter()
    for c, caja in zip(cuerpos, cajas, strict=True):
        if rayo_caja(o, d, *caja) < math.inf:
            rayo_triangulos(o, d, c)
    print(f"P5 rayo contra 400 k triángulos, ahora: {_ms(t):6.1f} ms")

    # P11 y P12: una malla de ~300 k triángulos.
    m = M.desde_brep(BRepPrimAPI_MakeSphere(20.0).Shape(), desviacion=0.0006)
    tri = m.vertices[m.caras]
    nor = np.cross(tri[:, 1] - tri[:, 0], tri[:, 2] - tri[:, 0])
    t = time.perf_counter()
    b"".join(struct.pack("<12fH", *n, *x[0], *x[1], *x[2], 0) for n, x in zip(nor, tri, strict=True))
    print(f"P11 STL binario de {len(tri)} triángulos, antes: {_ms(t):6.0f} ms")
    t = time.perf_counter()
    r = np.zeros(len(tri), dtype=[("n", "<f4", 3), ("v", "<f4", (3, 3)), ("a", "<u2")])
    r["n"], r["v"] = nor, tri
    r.tobytes()
    print(f"P11 STL binario de {len(tri)} triángulos, ahora: {_ms(t):6.0f} ms")
    n, he = len(m.vertices), M._medias_aristas(m.caras)
    t = time.perf_counter()
    directa = he[:, 0] * n + he[:, 1]
    _ = len(np.unique(directa)) == len(directa) and bool(np.isin(he[:, 1] * n + he[:, 0], directa).all())
    print(f"P12 es_cerrada, antes: {_ms(t):6.0f} ms")
    t = time.perf_counter()
    m.es_cerrada()
    print(f"P12 es_cerrada, ahora: {_ms(t):6.0f} ms")


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
    elif modo == "memoria":
        memoria()
    elif modo == "interfaz":
        interfaz()
    elif modo == "recalculo" and len(sys.argv) > 2:
        recalculo(sys.argv[2])
    else:
        sys.exit(__doc__)
