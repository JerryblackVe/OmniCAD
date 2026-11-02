# -*- coding: utf-8 -*-
"""Banco de Reconstruir sólido (RI-1, docs/plan_reconstruir_solido.md).

30 piezas generadas con la API de OmniCAD (12 prismáticas, 8 torneadas, 6 con empalmes y chaflanes, 4 con patrones),
exportadas a STL, OBJ y 3MF, con su respuesta conocida (volumen, área, caja, caras y pasos). Más los STL reales de
Gerardo, que se leen sin tocarlos. Todo lo generado queda en `evidencias/` (fuera de git).

Uso, desde `clon/`:
    .venv/Scripts/python.exe ../scripts/turno.py -- .venv/Scripts/python.exe ../scripts/bench_reconstruir.py generar
    .venv/Scripts/python.exe ../scripts/turno.py --plazo 3000 -- .venv/Scripts/python.exe ../scripts/bench_reconstruir.py correr
    .venv/Scripts/python.exe ../scripts/bench_reconstruir.py correr P02 T03        (solo esas piezas)
    .venv/Scripts/python.exe ../scripts/bench_reconstruir.py reales [filtro ...]   (STL de Gerardo)
    .venv/Scripts/python.exe ../scripts/bench_reconstruir.py medir 200000          (fase 2 con N triángulos)
`generar` imprime la tabla de respuestas; `correr` y `reales` reconstruyen cada pieza en su propio proceso, con tope
de tiempo y memoria, y escriben la tabla contra las metas del plan en `evidencias/reconstruir_2026-11-01/`.
"""
import json
import os
import subprocess
import sys
import time
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ / "clon"))
CARPETA = RAIZ / "evidencias" / "reconstruir_2026-11-01"
BANCO = CARPETA / "banco"
RESPUESTAS = BANCO / "respuestas.json"
STL_REALES = Path(r"C:\Users\mosos\Desktop\STL")
FORMATOS = (("stl", "stl_binario"), ("obj", "obj"), ("3mf", "3mf"))
TOPE_PIEZA_S = 600
# Metas del plan, sin tocar (docs/plan_reconstruir_solido.md › Metas propuestas).
META_DESVIO_MM, META_VOLUMEN, META_CARAS = 0.1, 0.005, 1.5


def _llamar(s, herramienta, **args):
    from omnicad import api
    r = api.llamar(s, herramienta, args)
    if not r["ok"]:
        raise RuntimeError(f"{herramienta}: {r['mensaje']}")
    return r["result"]


def _boceto(s, plano, puntos, circulos=()):
    """Boceto con un polígono cerrado y círculos (centro, radio): un perfil con sus huecos."""
    lineas = [{"type": "line", "start": a, "end": b} for a, b in zip(puntos, puntos[1:] + puntos[:1], strict=True)]
    redondos = [{"type": "circle", "center": c, "radius": r} for c, r in circulos]
    return _llamar(s, "sketch_from_spec", plane=plano, entities=lineas + redondos)["sketch"]["id"]


def _caja(s, largo, ancho, alto, **k):
    return _llamar(s, "create_box", length=largo, width=ancho, height=alto, **k)


def _prisma(s, plano, puntos, distancia, circulos=(), **k):
    return _llamar(s, "extrude", sketch=_boceto(s, plano, puntos, circulos), profile="largest", distance=distancia, **k)


def _giro(s, puntos, entidades=None):
    """Revolución 360° alrededor de Z de un perfil en XZ (x = radio, y = altura)."""
    if entidades is None:
        entidades = [{"type": "line", "start": a, "end": b} for a, b in zip(puntos, puntos[1:] + puntos[:1], strict=True)]
    sk = _llamar(s, "sketch_from_spec", plane="XZ", entities=entidades)["sketch"]["id"]
    return _llamar(s, "revolve", sketch=sk, profile=0, axis="z", angle=360)


def _agujero(s, puntos, diametro, cara=">Z", **k):
    return _llamar(s, "create_hole", face=cara, diameter=diametro, points=puntos, **k)


# ---------------------------------------------------------------- 12 prismáticas
def p01(s):
    _caja(s, 60, 40, 20)


def p02(s):
    _caja(s, 80, 50, 8)
    _agujero(s, [[x, y, 8] for x in (-30, 30) for y in (-15, 15)], 6, through_all=True)


def p03(s):
    _prisma(s, "XY", [[0, 0], [50, 0], [50, 12], [15, 12], [15, 35], [0, 35]], 30)


def p04(s):
    _caja(s, 60, 40, 15)
    _prisma(s, "XY", [[-20, -10], [20, -10], [20, 10], [-20, 10]], 10, operation="cut", start="offset", start_offset=5)


def p05(s):
    _caja(s, 60, 60, 5)
    _caja(s, 40, 40, 10, z=5, operation="join")
    _caja(s, 20, 20, 10, z=15, operation="join")


def p06(s):
    _caja(s, 70, 70, 10)
    _llamar(s, "create_cylinder", diameter=30, height=20, z=10, operation="join")
    _agujero(s, [[0, 0, 30]], 16, cara=">Z", through_all=True)


def p07(s):
    sk = _llamar(s, "sketch_from_spec", plane="XY", entities=[
        {"type": "slot", "kind": "center_to_center", "points": [[-25, 0], [25, 0]], "width": 24},
        {"type": "circle", "center": [-25, 0], "radius": 5}, {"type": "circle", "center": [25, 0], "radius": 5}])
    _llamar(s, "extrude", sketch=sk["sketch"]["id"] if isinstance(sk.get("sketch"), dict) else sk, profile="largest", distance=10)


def p08(s):
    _prisma(s, "XZ", [[-30, 0], [30, 0], [30, 25], [24, 25], [24, 6], [-24, 6], [-24, 25], [-30, 25]], 60)


def p09(s):
    _caja(s, 60, 40, 25)
    _agujero(s, [[-15, 0, 25]], 10, depth=12)
    _agujero(s, [[15, 0, 25]], 8, through_all=True, hole_type="counterbore", counterbore_diameter=14, counterbore_depth=6)


def p10(s):
    _caja(s, 50, 40, 30)
    _agujero(s, [[0, 0, 30]], 10, through_all=True)
    _agujero(s, [[25, 0, 15]], 8, cara=">X", through_all=True)


def _ele(s):
    _prisma(s, "XZ", [[0, 0], [60, 0], [60, 6], [6, 6], [6, 45], [0, 45]], 40)


def p11(s):
    _ele(s)
    _llamar(s, "move_body", body=_unico(s), rotate=[20, 0, 30], pivot="origin")


def p12(s):
    _ele(s)
    y = -20
    _agujero(s, [[20, y, 6], [45, y, 6]], 6, cara="%PLANE and nearest:[30,-20,6]", through_all=True)
    _agujero(s, [[6, y, 15], [6, y, 35]], 6, cara="%PLANE and nearest:[6,-20,25]", through_all=True)


# ---------------------------------------------------------------- 8 torneadas
def t01(s):
    _llamar(s, "create_cylinder", diameter=30, height=50)


def t02(s):
    _giro(s, [[0, 0], [20, 0], [20, 15], [12, 15], [12, 45], [8, 45], [8, 70], [0, 70]])


def t03(s):
    _giro(s, [[10, 0], [30, 0], [30, 6], [16, 6], [16, 40], [10, 40]])


def t04(s):
    _giro(s, [[0, 0], [25, 0], [10, 40], [0, 40]])


def t05(s):
    _giro(s, None, [{"type": "line", "start": [0, 0], "end": [12, 0]}, {"type": "line", "start": [12, 0], "end": [12, 40]},
                    {"type": "arc", "start": [12, 40], "mid": [8.485281, 48.485281], "end": [0, 52]},
                    {"type": "line", "start": [0, 52], "end": [0, 0]}])


def t06(s):
    _giro(s, [[8, 0], [35, 0], [35, 4], [25, 12], [35, 20], [35, 24], [8, 24]])


def t07(s):
    _llamar(s, "create_torus", major_radius=30, minor_radius=6)


def t08(s):
    t02(s)
    _llamar(s, "move_body", body=_unico(s), rotate=[35, 15, 0], pivot="origin")


# ---------------------------------------------------------------- 6 con empalmes y chaflanes
def e01(s):
    _caja(s, 60, 40, 20)
    _llamar(s, "fillet", edges="|Z", radius=6)


def e02(s):
    _caja(s, 60, 40, 20)
    _llamar(s, "fillet", edges=">Z", radius=3)


def e03(s):
    _caja(s, 60, 40, 20)
    _llamar(s, "chamfer", edges=">Z", distance=2)


def e04(s):
    _llamar(s, "create_cylinder", diameter=40, height=30)
    _llamar(s, "chamfer", edges=">Z", distance=2)
    _llamar(s, "fillet", edges="<Z", radius=3)


def e05(s):
    _caja(s, 70, 50, 12)
    _llamar(s, "fillet", edges="|Z", radius=8)
    _agujero(s, [[0, 0, 12]], 14, through_all=True)
    _llamar(s, "chamfer", edges="nearest:[7,0,12]", distance=1.5)


def e06(s):
    _prisma(s, "XZ", [[0, 0], [50, 0], [50, 10], [10, 10], [10, 40], [0, 40]], 30)
    _llamar(s, "fillet", edges="nearest:[10,-15,10]", radius=4)
    _llamar(s, "chamfer", edges="nearest:[50,-15,10]", distance=2)


# ---------------------------------------------------------------- 4 con patrones
def _ultimo(s):
    return s.doc.operaciones[-1].id


def r01(s):
    _caja(s, 90, 70, 6)
    _agujero(s, [[-30, -20, 6]], 5, through_all=True)
    _llamar(s, "rectangular_pattern", features=[_ultimo(s)], x_count=4, x_spacing=20, y_count=3, y_spacing=20)


def r02(s):
    _llamar(s, "create_cylinder", diameter=80, height=10)
    _agujero(s, [[28, 0, 10]], 8, through_all=True)
    _llamar(s, "circular_pattern", features=[_ultimo(s)], count=6, axis="z", total_angle=360)


def r03(s):
    _caja(s, 100, 40, 6)
    _caja(s, 4, 40, 15, x=-40, z=6, operation="join")
    _llamar(s, "rectangular_pattern", features=[_ultimo(s)], x_count=5, x_spacing=20)


def r04(s):
    _llamar(s, "create_cylinder", diameter=80, height=12)
    _prisma(s, "XY", [[33, -4], [45, -4], [45, 4], [33, 4]], 12, operation="cut")
    _llamar(s, "circular_pattern", features=[_ultimo(s)], count=8, axis="z", total_angle=360)


def _unico(s):
    return next(iter(s.doc.estado_final.cuerpos))


PIEZAS = {"P01": ("prismatica", "bloque", p01), "P02": ("prismatica", "placa 4 agujeros", p02),
          "P03": ("prismatica", "perfil L", p03), "P04": ("prismatica", "bolsillo", p04),
          "P05": ("prismatica", "tres escalones", p05), "P06": ("prismatica", "brida con cubo", p06),
          "P07": ("prismatica", "ojal doble", p07), "P08": ("prismatica", "canal U", p08),
          "P09": ("prismatica", "ciego y abocardado", p09), "P10": ("prismatica", "agujero lateral", p10),
          "P11": ("prismatica", "ángulo girado", p11), "P12": ("prismatica", "ángulo con agujeros", p12),
          "T01": ("torneada", "cilindro", t01), "T02": ("torneada", "eje escalonado", t02),
          "T03": ("torneada", "buje con pestaña", t03), "T04": ("torneada", "tronco de cono", t04),
          "T05": ("torneada", "punta esférica", t05), "T06": ("torneada", "polea en V", t06),
          "T07": ("torneada", "toroide", t07), "T08": ("torneada", "eje girado", t08),
          "E01": ("empalmes", "aristas verticales", e01), "E02": ("empalmes", "borde superior", e02),
          "E03": ("empalmes", "chaflán superior", e03), "E04": ("empalmes", "cilindro con los dos", e04),
          "E05": ("empalmes", "placa con agujero", e05), "E06": ("empalmes", "L con los dos", e06),
          "R01": ("patrones", "rejilla de agujeros", r01), "R02": ("patrones", "círculo de agujeros", r02),
          "R03": ("patrones", "nervios", r03), "R04": ("patrones", "muescas", r04)}


def respuesta(clave):
    """Arma la pieza, la exporta y devuelve su respuesta conocida."""
    from omnicad import api
    from omnicad.api import selectores as sl
    tipo, nombre, armar = PIEZAS[clave]
    s = api.Sesion()
    armar(s)
    cuerpo = s.doc.estado_final.cuerpos[_unico(s)]
    sf = _llamar(s, "get_physical_properties", bodies=[cuerpo.id])["bodies"][0]
    fallas = [o.id for o, r in zip(s.doc.operaciones, s.doc.resultados, strict=True) if r.estado == "error"]
    if fallas or len(s.doc.estado_final.cuerpos) != 1:
        raise RuntimeError(f"{clave}: {fallas or 'más de un cuerpo'}")
    for extension, formato in FORMATOS:
        _llamar(s, "export_mesh", path=str(BANCO / f"{clave}.{extension}"), format=formato, overwrite=True)
    s.guardar(str(BANCO / f"{clave}.omnicad"), sobrescribir=True)
    from omnicad.nucleo import malla as ml
    m = ml.leer(str(BANCO / f"{clave}.stl"))
    return {"pieza": clave, "tipo": tipo, "nombre": nombre, "volumen": sf["volume"], "area": sf["area"],
            "caja": sf["bounding_box"],
            "caras": len(sl.listar(cuerpo.forma, "cara")), "pasos": len(s.doc.operaciones),
            "triangulos": len(m.caras), "cerrada": m.es_cerrada()}


def generar(claves):
    BANCO.mkdir(parents=True, exist_ok=True)
    previas = json.loads(RESPUESTAS.read_text(encoding="utf-8")) if RESPUESTAS.exists() else {}
    for k in claves:
        previas[k] = respuesta(k)
    RESPUESTAS.write_text(json.dumps(previas, indent=1, ensure_ascii=False), encoding="utf-8")
    print(f"{'pieza':5} {'tipo':10} {'nombre':22} {'volumen':>11} {'área':>10} {'caja':>20} {'caras':>5} {'pasos':>5} "
          f"{'triáng':>7} cerrada")
    for k in sorted(previas):
        r = previas[k]
        print(f"{k:5} {r['tipo']:10} {r['nombre']:22} {r['volumen']:11.2f} {r['area']:10.2f} "
              f"{'x'.join(f'{x:.1f}' for x in r['caja']['size']):>20} {r['caras']:5d} {r['pasos']:5d} "
              f"{r['triangulos']:7d} {r['cerrada']}")
    print(f"\n{len(previas)} piezas en {BANCO}")


# ---------------------------------------------------------------- reconstruir
def reconstruir_uno(ruta, unidades="mm"):
    """Inserta la malla en un documento nuevo, reconstruye y verifica abrir + editar + recalcular. Imprime JSON."""
    from omnicad import api
    t0 = time.perf_counter()
    s = api.Sesion()
    malla = _llamar(s, "insert_file", path=str(ruta), mesh_units=unidades)["new_bodies"][0]
    r = _llamar(s, "reconstruct_from_mesh", body=malla, tolerance=META_DESVIO_MM)
    t = time.perf_counter() - t0
    salida = {k: r.get(k) for k in ("max_deviation", "mean_deviation", "within_tolerance_percent", "volume_difference_percent",
                                    "faces", "steps_created", "valid", "strategy", "unrecovered", "tolerance_met")}
    salida.update(segundos=round(t, 1), zonas=len(r.get("zones_out_of_tolerance") or []))
    # Abrir, editar y recalcular: la promesa de los criterios de éxito.
    ruta_doc = CARPETA / "salidas" / f"{Path(ruta).stem}.omnicad"
    ruta_doc.parent.mkdir(parents=True, exist_ok=True)
    s.guardar(str(ruta_doc), sobrescribir=True)
    otra = api.Sesion()
    otra.abrir(str(ruta_doc))
    salida["errores_al_abrir"] = sum(x.estado == "error" for x in otra.doc.resultados)
    _llamar(otra, "recompute_all")
    salida["errores_al_recalcular"] = sum(x.estado == "error" for x in otra.doc.resultados)
    salida["edicion"] = _probar_edicion(otra)
    print("RESULTADO " + json.dumps(salida, ensure_ascii=False), flush=True)


def _probar_edicion(s):
    """Cambia un 5 % la distancia de la primera extrusión o el ángulo de la primera revolución y mira que recalcule."""
    from omnicad import api
    for o in s.doc.operaciones:
        for clave in ("distancia", "angulo"):
            valor = o.p.get(clave)
            if valor is None or o.TIPO not in ("extrusion", "extruir", "revolucion", "revolver"):
                continue
            try:
                numero = float(str(valor).split()[0])
            except ValueError:
                continue
            nuevo = numero * (0.95 if clave == "distancia" else 0.9)
            unidad = "mm" if clave == "distancia" else "deg"
            r = api.llamar(s, "edit_feature", {"feature": o.id, "params": {clave: f"{nuevo:.6f} {unidad}"}})
            rojos = sum(x.estado == "error" for x in s.doc.resultados)
            return {"paso": o.id, "ok": r["ok"] and not rojos, "mensaje": r.get("mensaje", f"{rojos} pasos en error")[:120]}
    return {"paso": None, "ok": None, "mensaje": "sin extrusión ni revolución para editar"}


def correr_lote(rutas):
    """Cada pieza en su proceso, con tope; devuelve {nombre: resultado}."""
    python = sys.executable
    salida = {}
    for nombre, ruta in rutas:
        t0 = time.perf_counter()
        try:
            r = subprocess.run([python, __file__, "uno", str(ruta)], capture_output=True, text=True, encoding="utf-8",
                               errors="replace", timeout=TOPE_PIEZA_S, cwd=RAIZ / "clon",
                               env=dict(os.environ, PYTHONIOENCODING="utf-8"))
            linea = next((x for x in r.stdout.splitlines() if x.startswith("RESULTADO ")), None)
            salida[nombre] = json.loads(linea[10:]) if linea else {"error": (r.stderr or r.stdout).strip()[-300:]}
        except subprocess.TimeoutExpired:
            salida[nombre] = {"error": f"pasó el tope de {TOPE_PIEZA_S} s"}
        salida[nombre].setdefault("segundos", round(time.perf_counter() - t0, 1))
        print(_fila(nombre, salida[nombre]), flush=True)
    return salida


def _metas(r, caras_original=None):
    """{meta: bool} de una pieza. None donde no hay respuesta conocida."""
    if "error" in r:
        return {"desvio": False, "volumen": False, "caras": False, "timeline": False}
    return {"desvio": r["max_deviation"] is not None and r["max_deviation"] <= META_DESVIO_MM,
            "volumen": r["volume_difference_percent"] is not None and abs(r["volume_difference_percent"]) <= 100 * META_VOLUMEN,
            "caras": None if not caras_original else r["faces"] <= META_CARAS * caras_original,
            "timeline": bool(r["valid"]) and r["errores_al_abrir"] == 0 and r["errores_al_recalcular"] == 0}


def _si(v):
    return "-" if v is None else "sí" if v else "NO"


def _fila(nombre, r, caras=None):
    if "error" in r:
        return f"{nombre:44} ERROR {r['error'][:110]}"
    m = _metas(r, caras)
    return (f"{nombre:44} {r['max_deviation'] if r['max_deviation'] is not None else float('nan'):8.3f} "
            f"{r['within_tolerance_percent'] or 0:6.1f} {r['volume_difference_percent'] or 0:7.2f} "
            f"{r['faces'] or 0:5d} {caras or 0:5d} {r['steps_created'] or 0:5d} {r['segundos']:6.1f} "
            f"{r.get('strategy') or '':10} {_si(m['desvio']):3} {_si(m['volumen']):3} {_si(m['caras']):3} {_si(m['timeline']):3}")


CABECERA = (f"{'pieza':44} {'desv.mm':>8} {'%tol':>6} {'%vol':>7} {'caras':>5} {'orig':>5} {'pasos':>5} {'seg':>6} "
            f"{'estrategia':10} {'dsv':3} {'vol':3} {'car':3} {'tml':3}")


def resumen_por_tipo(resultados, respuestas):
    grupos = {}
    for k, r in resultados.items():
        grupos.setdefault(respuestas[k]["tipo"] if k in respuestas else "real", []).append((k, r))
    lineas = [f"\n{'tipo':11} {'piezas':>6} {'desvío':>7} {'volumen':>8} {'caras':>6} {'timeline':>9} {'todas':>6}"]
    for tipo, filas in grupos.items():
        cuenta = {"desvio": 0, "volumen": 0, "caras": 0, "timeline": 0}
        todas = 0
        for k, r in filas:
            m = _metas(r, respuestas[k]["caras"] if k in respuestas else None)
            for clave in cuenta:
                cuenta[clave] += bool(m[clave])
            todas += all(v is not False for v in m.values())
        lineas.append(f"{tipo:11} {len(filas):6d} {cuenta['desvio']:7d} {cuenta['volumen']:8d} {cuenta['caras']:6d} "
                      f"{cuenta['timeline']:9d} {todas:6d}")
    return "\n".join(lineas)


def correr(claves):
    respuestas = json.loads(RESPUESTAS.read_text(encoding="utf-8"))
    print(CABECERA, flush=True)
    resultados = correr_lote([(k, BANCO / f"{k}.stl") for k in claves])
    print("\n" + CABECERA)
    for k, r in resultados.items():
        print(_fila(k, r, respuestas[k]["caras"]))
    print(resumen_por_tipo(resultados, respuestas))
    previos_ruta = CARPETA / "tabla_banco.json"
    previos = json.loads(previos_ruta.read_text(encoding="utf-8")) if previos_ruta.exists() else {}
    previos.update(resultados)
    previos_ruta.write_text(json.dumps(previos, indent=1, ensure_ascii=False), encoding="utf-8")


def reales(filtros):
    rutas = sorted(STL_REALES.rglob("*.stl"))
    if filtros:
        rutas = [r for r in rutas if any(f.lower() in str(r).lower() for f in filtros)]
    vistos, lote = set(), []
    for r in rutas:
        if (r.stat().st_size, r.name.rsplit(" ", 1)[0]) in vistos:      # las copias idénticas del mismo archivo, una vez
            continue
        vistos.add((r.stat().st_size, r.name.rsplit(" ", 1)[0]))
        lote.append((f"{r.parent.name[:12]}/{r.stem[:30]}", r))
    print(CABECERA, flush=True)
    resultados = correr_lote(lote)
    print(resumen_por_tipo(resultados, {}))
    (CARPETA / "tabla_reales.json").write_text(json.dumps(resultados, indent=1, ensure_ascii=False), encoding="utf-8")


def _pico_memoria():
    """Pico de memoria de este proceso en bytes (se mide con la API de Windows o `resource`: psutil no está instalado)."""
    if os.name == "nt":
        import ctypes
        from ctypes import wintypes

        class Contadores(ctypes.Structure):
            _fields_ = [("cb", wintypes.DWORD), ("faltas", wintypes.DWORD), ("pico", ctypes.c_size_t), ("actual", ctypes.c_size_t)]
            _fields_ += [(f"x{k}", ctypes.c_size_t) for k in range(6)]
        c = Contadores()
        c.cb = ctypes.sizeof(c)
        ctypes.WinDLL("psapi").GetProcessMemoryInfo(ctypes.c_void_p(-1), ctypes.byref(c), c.cb)      # -1: este proceso
        return c.pico
    import resource
    return resource.getrusage(resource.RUSAGE_SELF).ru_maxrss * 1024


def _cuadruplicar(m):
    """Cada triángulo en cuatro: `refinar_triangulos` corta en 100.000 para cuidar la ventana."""
    import numpy as np

    from omnicad.nucleo import malla as ml
    F = m.caras
    medios, inversa = np.unique(np.sort(F[:, [0, 1, 1, 2, 2, 0]].reshape(-1, 2), axis=1), axis=0, return_inverse=True)
    ab, bc, ca = (len(m.vertices) + inversa.reshape(-1, 3)).T
    a, b, c = F.T
    return ml.Malla(np.r_[m.vertices, m.vertices[medios].mean(1)],
                    np.r_[np.c_[a, ab, ca], np.c_[ab, b, bc], np.c_[ca, bc, c], np.c_[ab, bc, ca]])


def medir(triangulos):
    """Con N triángulos (paso 7): tiempo y pico de memoria de medir las formas (fase 2) y de reconstruir entero (la meta)."""
    import cProfile
    import pstats

    from omnicad import api
    from omnicad.nucleo import formas_malla as fm
    from omnicad.nucleo import geometria as geo
    from omnicad.nucleo import malla as ml
    forma = geo.booleano(geo.caja(120, 80, 40, (-60, -40, 0)), geo.cilindro(20, 60, (0, 0, -10)), "cortar")
    m = ml.desde_brep(forma, refinamiento="personalizado", desviacion=0.05, angulo=10.0)
    while len(m.caras) < triangulos:
        m = _cuadruplicar(m)
    print(f"{len(m.caras)} triángulos", flush=True)
    perfil = cProfile.Profile()
    t0 = time.perf_counter()
    perfil.enable()
    ficha = fm.analizar(m)
    perfil.disable()
    print(f"formas: {time.perf_counter() - t0:.1f} s, pico {_pico_memoria() / 2**30:.2f} GB, {len(ficha['shapes'])} formas, "
          f"{ficha['unclassified_percent']:.2f} % sin clasificar", flush=True)
    pstats.Stats(perfil).sort_stats("cumulative").print_stats(14)
    ruta = CARPETA / "medir.stl"
    ml.escribir(m, str(ruta))
    s = api.Sesion()
    malla = _llamar(s, "insert_file", path=str(ruta))["new_bodies"][0]
    t0 = time.perf_counter()
    r = _llamar(s, "reconstruct_from_mesh", body=malla, tolerance=META_DESVIO_MM)
    print(f"reconstruir: {time.perf_counter() - t0:.1f} s, pico {_pico_memoria() / 2**30:.2f} GB, desvío {r['max_deviation']:.4f} mm, "
          f"{r['faces']} caras, {r['steps_created']} pasos, cumple {r['tolerance_met']}", flush=True)
    ruta.unlink()


if __name__ == "__main__":
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    orden = sys.argv[1] if len(sys.argv) > 1 else "generar"
    resto = sys.argv[2:]
    if orden == "generar":
        generar(resto or list(PIEZAS))
    elif orden == "correr":
        correr(resto or list(PIEZAS))
    elif orden == "reales":
        reales(resto)
    elif orden == "uno":
        reconstruir_uno(Path(resto[0]))
    elif orden == "medir":
        medir(int(resto[0]) if resto else 200000)
    else:
        sys.exit(__doc__)
