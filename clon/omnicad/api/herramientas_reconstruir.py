# -*- coding: utf-8 -*-
"""
Reconstruir sólido (docs/plan_reconstruir_solido.md, fases 1 a 3): comparar dos cuerpos (`compare_to_mesh`), medir las formas
de una malla (`analyze_mesh_features`) y rehacer la malla como pieza con timeline (`reconstruct_from_mesh`). El núcleo está en
`nucleo/comparar_malla.py`, `nucleo/formas_malla.py` y `nucleo/reconstruir_malla.py`; acá se vuelve pasos normales llamando a
las herramientas de siempre, así que cada paso se edita como cualquier otro.
"""
import time

import numpy as np

from ..nucleo import comparar_malla as cm
from ..nucleo import formas_malla as fm
from ..nucleo import geometria as geo
from ..nucleo import malla as ml
from ..nucleo import reconstruir_malla as rm
from . import selectores as sl
from .errores import ErrorAPI, error
from .herramientas_malla import _cuerpos
from .registro import herramienta, llamar

_MUESTRAS_VUELTA = 15000               # el juez de cada vuelta de corrección: más liviano que el del informe
_MEJORA_MINIMA = 0.01                  # una corrección se queda si baja la desviación media al menos esto (relativo)
_TOPE_CAPAS = 30
_PLAZO = 180.0                         # segundos: pasado esto no se prueban más estrategias ni correcciones (la última real tardó 10 min)
_SIN_CLASIFICAR = 25.0                 # % de área: desde acá conviene medir de nuevo con la tolerancia pedida


def _r(x, d=4):
    return None if x is None else round(float(x), d) + 0.0


def _llamar(sesion, nombre, **args):
    r = llamar(sesion, nombre, args)
    if not r["ok"]:
        raise error("OPERATION_FAILED", f"{nombre}: {r['mensaje']}")
    return r["result"]


def _punto(p):
    return "[" + ",".join(f"{x:.6f}" for x in p) + "]"


def _informe(c):
    """Resultado del juez, con las claves y el redondeo de la API."""
    return {"max_deviation": _r(c["max_deviation"]), "mean_deviation": _r(c["mean_deviation"], 5),
            "p95_deviation": _r(c["p95_deviation"]), "within_tolerance_percent": _r(c["within_tolerance_percent"], 3),
            "volume_difference_percent": _r(c["volume_difference_percent"], 4), "overlap_iou": _r(c["iou"], 5),
            "bbox_difference": _r(c["bbox_difference"]), "zones_out_of_tolerance": c["zones"], "zones_total": c["zones_total"]}


def _validar_tolerancia(tolerance):
    if not 0 < tolerance < 1e4:
        raise error("INVALID_ARGUMENTS", f"tolerance tiene que ser mayor que cero, en mm (recibió {tolerance:g}).")


@herramienta("compare_to_mesh", "inspeccion", "Compara dos cuerpos, cada uno sólido, superficie o malla (el mapa de "
             "desviación de INSPECCIONAR › Mapa de desviación, con números): desviación en los dos sentidos (máxima, media, "
             "percentil 95), % de superficie dentro de tolerance, diferencia de volumen, solapamiento (intersección sobre "
             "unión, solo con cuerpos cerrados) y zonas fuera de tolerancia (centro, caja, área, cuánto sobra y cuánto "
             "falta). Signo: excess_mm es material que body tiene de más respecto de reference; missing_mm, lo que le falta. "
             "Sirve para una pieza contra su malla y para una versión vieja contra una nueva. Puntos al azar con semilla "
             "fija: dos corridas dan lo mismo. No cambia el documento.")
def compare_to_mesh(sesion, body: str, reference: str, tolerance: float = 0.1, samples: int = 50000):
    """
    body: id o nombre del cuerpo a juzgar (sólido, superficie o malla).
    reference: id o nombre del cuerpo de referencia (malla, sólido o superficie).
    tolerance: desviación aceptada en mm; decide el % dentro de tolerancia y las zonas.
    samples: puntos por lado, entre 1000 y 2.000.000; más puntos ven zonas más chicas y tardan más.
    """
    _validar_tolerancia(tolerance)
    a, b = sesion.cuerpo(body), sesion.cuerpo(reference)
    if a.id == b.id:
        raise error("INVALID_ARGUMENTS", "body y reference son el mismo cuerpo.")
    c = cm.comparar(a.forma, b.forma, tolerancia=tolerance, muestras=samples)
    return dict(_informe(c), body=a.id, reference=b.id, tolerance=tolerance, volume_body=_r(c["volume_a"], 3),
                volume_reference=_r(c["volume_b"], 3), volume_difference=_r(c["volume_difference"], 3),
                body_to_reference={k: _r(v) for k, v in c["a_to_b"].items()},
                reference_to_body={k: _r(v) for k, v in c["b_to_a"].items()}, closed=c["closed"])


@herramienta("show_deviation_map", "inspeccion", "Agrega el Mapa de desviación de INSPECCIONAR a la carpeta Análisis: pinta body "
             "según cuánto se aparta de reference, verde a amarillo dentro de tolerance, rojo donde sobra y azul donde falta. "
             "get_viewport_image lo dibuja; manage_analysis lo oculta o lo quita. Los números salen de compare_to_mesh.",
             modifica=True)
def show_deviation_map(sesion, body: str, reference: str, tolerance: float = 0.1, name: str | None = None):
    """
    body: id o nombre del cuerpo a pintar.
    reference: id o nombre del cuerpo de referencia.
    tolerance: desviación aceptada en mm.
    name: nombre del análisis; vacío = «Desviación1», «Desviación2»…
    """
    _validar_tolerancia(tolerance)
    a, b = sesion.cuerpo(body), sesion.cuerpo(reference)
    if a.id == b.id:
        raise error("INVALID_ARGUMENTS", "body y reference son el mismo cuerpo.")
    nombre = sesion.doc.agregar_analisis("desviacion", {"cuerpos": [a.id], "referencia": b.id, "tolerancia": tolerance}, name)
    return {"analysis": nombre, "body": a.id, "reference": b.id, "tolerance": tolerance}


@herramienta("analyze_mesh_features", "malla", "Mide las formas de una malla: planos, cilindros, conos, esferas y toros, cada "
             "uno con sus medidas, área, triángulos, error de ajuste (fit_error, max_error) y formas vecinas, más el % sin "
             "clasificar. También agujeros (diámetro, profundidad, eje, pasante), patrones de agujeros, eje de revolución, "
             "simetrías y si la malla parece de CAD o de un escaneo. Sirve para que un agente entienda una malla sin leer "
             "triángulos. tolerance es cuánto puede apartarse un vértice de la forma; subila en mallas con ruido. Dos corridas "
             "dan la misma ficha. No cambia el documento.")
def analyze_mesh_features(sesion, body: str, tolerance: float | None = None):
    """
    body: id o nombre del cuerpo de malla.
    tolerance: en mm; vacío = 0,02 % de la diagonal de la caja.
    """
    if tolerance is not None:
        _validar_tolerancia(tolerance)
    (cuerpo,) = _cuerpos(sesion, body, que="body")
    return dict(fm.analizar(cuerpo.forma, tolerancia=tolerance), body=cuerpo.id)


# ---------------------------------------------------------------- construir
def _plano_trabajo(sesion, marco, nombre):
    """Referencia para `sketch_from_spec` y el plano real, con toda su precisión."""
    if abs(marco["offset"]) < 1e-6:
        return marco["plane"], geo.Plano(marco["plane"])
    pid = _llamar(sesion, "create_construction_plane", plane=marco["plane"], offset=marco["offset"], name=nombre)["plane"]["id"]
    return pid, sesion.doc.estado_final.planos[pid]


def _perfiles(sesion, sketch, regs):
    """Qué perfiles del boceto son las regiones: se reconocen por su área."""
    if len(regs) == 1:
        return "largest"
    perfiles = _llamar(sesion, "get_sketch", sketch=sketch)["profiles"]
    elegidos = []
    for r in sorted(regs, key=lambda x: -x["area"]):            # de a uno: dos regiones de igual área no pueden ser el mismo perfil
        if not perfiles:
            break
        p = min(perfiles, key=lambda q: abs(q["area"] - r["area"]))
        perfiles.remove(p)
        elegidos.append(p["index"])
    return sorted(elegidos)


def _capa(sesion, plano_ref, regs, h0, h1, exactos, fit, nombre, operacion, cuerpo=None):
    """Una extrusión entre dos alturas, con sus regiones en un boceto."""
    ents = rm.entidades([c for r in regs for c in rm.curvas_region(r, fit, exactos)])
    sk = _llamar(sesion, "sketch_from_spec", plane=plano_ref, entities=ents, name=nombre)["sketch"]["id"]
    args = {"sketch": sk, "profile": _perfiles(sesion, sk, regs), "distance": round(h1 - h0, 4), "operation": operacion,
            "reverse": False}
    if cuerpo is not None:
        args["target"] = cuerpo
    if h0 > 1e-6:
        args.update(start="offset", start_offset=round(h0, 4))
    return _llamar(sesion, "extrude", **args)


def _agujero(sesion, h, cuerpo):
    entrada = h["entry"]
    args = {"face": f"%PLANE and nearest:{_punto(entrada)}", "points": [entrada], "diameter": h["diameter"], "body": cuerpo}
    if h["through"]:
        args["through_all"] = True
    else:
        args["depth"] = h["depth"]
    if h["counterbore"]:
        args.update(hole_type="counterbore", counterbore_diameter=h["counterbore"]["diameter"],
                    counterbore_depth=h["counterbore"]["depth"])
    _llamar(sesion, "create_hole", **args)
    return sesion.doc.operaciones[-1].id


def _patron(sesion, g, cuerpo):
    op = _agujero(sesion, g["hole"], cuerpo)
    if g["kind"] == "rectangular":
        args = {"features": [op], "x_count": g["counts"][0], "x_spacing": g["steps"][0], "axis1": g["axes"][0]}
        if len(g["counts"]) > 1:
            args.update(y_count=g["counts"][1], y_spacing=g["steps"][1], axis2=g["axes"][1])
        _llamar(sesion, "rectangular_pattern", **args)
        return
    o, a, e = np.array(g["axis_point"], float), np.array(g["axis"], float), np.array(g["hole"]["entry"], float)
    centro = o + a * float((e - o) @ a)                         # un eje por dos puntos pide vértices: va por la cara de entrada
    eje = _llamar(sesion, "create_construction_axis", type="perpendicular_cara", references=[f"%PLANE and nearest:{_punto(e)}"],
                  location=[float(x) for x in centro], body=cuerpo, name="Eje del patrón")
    _llamar(sesion, "circular_pattern", features=[op], count=g["count"], axis=eje["axis"]["id"], total_angle=360)


def _agujeros(sesion, ficha, cuerpo, faltas, salvo):
    """Agujeros y patrones. `salvo`: los que ya están en el perfil (coaxiales a la revolución)."""
    planes = [h for h in rm.plan_agujeros(ficha) if not salvo(h)]
    sueltos, grupos = rm.agrupar_patrones(ficha, planes)
    for g in grupos:
        try:
            with sesion.transaccion():
                _patron(sesion, g, cuerpo)
        except ErrorAPI as e:
            sueltos.append(g["hole"])
            faltas.append(f"Patrón de agujeros de {g['hole']['diameter']:g} mm: {e.mensaje}")
    for h in sueltos:
        try:
            with sesion.transaccion():
                _agujero(sesion, h, cuerpo)
        except ErrorAPI as e:
            faltas.append(f"Agujero de {h['diameter']:g} mm en {h['entry']}: {e.mensaje}")


def _acabados(sesion, ficha, d, cuerpo, faltas):
    grupos, sueltos = rm.plan_acabados(ficha, d)
    for g in grupos:
        edges = [f"nearest:{_punto(p)}" for p in g["edges"]]
        try:
            with sesion.transaccion():
                if g["kind"] == "fillet":
                    _llamar(sesion, "fillet", edges=edges, radius=g["size"], body=cuerpo)
                elif abs(g["size"] - g["size2"]) < 0.01:
                    _llamar(sesion, "chamfer", edges=edges, distance=g["size"], body=cuerpo)
                else:
                    _llamar(sesion, "chamfer", edges=edges, distance=g["size"], distance2=g["size2"], body=cuerpo,
                            type="two_distances")
        except ErrorAPI as e:
            faltas.append(f"{'Empalme' if g['kind'] == 'fillet' else 'Chaflán'} de {g['size']:g} mm: {e.mensaje}")
    for f in sueltos:
        faltas.append(f"{f['type']} {f['id']} (área {f['area']:g} mm²): no se pudo ubicar su arista")


def _prisma(sesion, m, ficha, d, tol, nombre, faltas):
    agujeros = rm.plan_agujeros(ficha)
    ref, plano = _plano_trabajo(sesion, rm.marco(d, m), f"Base de {nombre}")
    pila = rm.capas(m, ficha, plano, ficha["tolerance"] * 2, agujeros)
    if not pila:
        raise error("OPERATION_FAILED", "La malla no da cortes cerrados: ¿está abierta? Probá repair_mesh.")
    if len(pila) > _TOPE_CAPAS:
        raise error("OPERATION_FAILED", f"En esta dirección harían falta {len(pila)} extrusiones apiladas: no es una pieza de capas.")
    fit = rm.desviacion_ajuste(tol)
    exactos = rm.circulos(ficha, plano, plano.normal)
    pila.sort(key=lambda c: -sum(r["area"] for r in c["regions"]) * (c["h1"] - c["h0"]))
    cuerpo = None
    for i, c in enumerate(pila, 1):
        r = _capa(sesion, ref, c["regions"], c["h0"], c["h1"], exactos, fit, f"Perfil {i} de {nombre}",
                  "new_body" if cuerpo is None else "join", cuerpo)
        if cuerpo is None:
            cuerpo = r["bodies_created"][0]["id"]
    _agujeros(sesion, ficha, cuerpo, faltas, lambda h: False)
    _acabados(sesion, ficha, plano.normal, cuerpo, faltas)
    return cuerpo


def _giro(sesion, m, ficha, o, a, tol, nombre, faltas):
    ref, plano = _plano_trabajo(sesion, rm.marco_eje(o, a), f"Corte de {nombre}")
    perfiles = rm.perfil_revolucion(m, plano, o, a, rm.desviacion_ajuste(tol), rm.circulos_revolucion(ficha, plano, o, a))
    if not perfiles:
        raise error("OPERATION_FAILED", "El corte por el eje no da un perfil cerrado.")
    ents = rm.entidades([c for p in perfiles for c in p["curves"]])
    for p in perfiles:
        if p["closing"] is not None:
            ents.append({"type": "line", "start": [float(rm._r(x)) for x in p["closing"][0]],
                         "end": [float(rm._r(x)) for x in p["closing"][1]], "centerline": True})
    if not any(p["closing"] is not None for p in perfiles):
        q = np.array([(np.asarray(o) - plano.origen) @ plano.u, (np.asarray(o) - plano.origen) @ plano.v])
        e = np.array([np.dot(a, plano.u), np.dot(a, plano.v)], float)
        ents.append({"type": "line", "start": [rm._r(x) for x in q], "end": [rm._r(x) for x in q + e * 10], "centerline": True})
    sk = _llamar(sesion, "sketch_from_spec", plane=ref, entities=ents, name=f"Perfil de {nombre}")["sketch"]["id"]
    r = _llamar(sesion, "revolve", sketch=sk, profile=_perfiles(sesion, sk, perfiles), angle=360)
    cuerpo = r["bodies_created"][0]["id"]

    def coaxial(h):
        return rm._paralelas(h["axis"], a) and np.linalg.norm(np.cross(a, np.subtract(h["entry"], o))) < 1e-2
    _agujeros(sesion, ficha, cuerpo, faltas, coaxial)
    return cuerpo


class _Probar(Exception):
    """Deshace lo construido en este intento."""


def _resto(sesion, resto, cuerpo, tol, k):
    """Suma o corta una cáscara residual: un prisma ajustado a ella."""
    b = rm.bloque(resto["mesh"], tol)
    if b is None:
        raise error("OPERATION_FAILED", "la cáscara no es un prisma")
    ref, plano = _plano_trabajo(sesion, rm.marco(b["direction"], resto["mesh"]), f"Corrección {k}")
    h = (resto["mesh"].vertices[np.unique(resto["mesh"].caras)] - plano.origen) @ plano.normal
    h0, h1 = float(h.min()), float(h.max())
    regs = rm.regiones(rm._lazos(resto["mesh"], plano.desplazado((h0 + h1) / 2)))
    if not regs:
        raise error("OPERATION_FAILED", "la cáscara no da un corte cerrado")
    _capa(sesion, ref, regs, h0, h1, (), rm.desviacion_ajuste(tol),
          f"Corrección {k}", "join" if resto["kind"] == "add" else "cut", cuerpo)


def _juez(sesion, cuerpo, m, tol, muestras=_MUESTRAS_VUELTA):
    return cm.comparar(sesion.cuerpo(cuerpo).forma, m, tolerancia=tol, muestras=muestras)


def _corregir(sesion, m, cuerpo, tol, vueltas, limite, faltas):
    """Vuelta de corrección: compara, suma lo que falta y corta lo que sobra. Se queda con cada corrección que mejora y
    corta sola si una vuelta entera no mejora nada."""
    registro = []
    if not m.es_cerrada():
        faltas.append("La malla no es cerrada: sin vuelta de corrección (necesita restar mallas).")
        return registro
    actual = _juez(sesion, cuerpo, m, tol)
    k = 0
    for vuelta in range(1, vueltas + 1):
        if actual["max_deviation"] <= tol:
            break
        if time.monotonic() > limite:
            faltas.append("La vuelta de corrección se cortó por tiempo.")
            break
        restos = rm.residuos(m, cm.a_malla(sesion.cuerpo(cuerpo).forma, tol), tol)
        hechas = 0
        for resto in restos:
            k += 1
            try:
                with sesion.transaccion():
                    _resto(sesion, resto, cuerpo, tol, k)
                    nuevo = _juez(sesion, cuerpo, m, tol)
                    if nuevo["mean_deviation"] > actual["mean_deviation"] * (1 - _MEJORA_MINIMA):
                        raise _Probar
            except (_Probar, ErrorAPI, geo.ErrorGeometria):
                continue
            actual = nuevo
            hechas += 1
        registro.append({"iteration": vuelta, "residuals": len(restos), "applied": hechas,
                         "max_deviation": _r(actual["max_deviation"]), "mean_deviation": _r(actual["mean_deviation"], 5)})
        if not hechas:
            break
    return registro


def _preparar(base, m, ficha, e):
    """Lo que necesita un intento, en el marco donde se modela: (e, base, malla objetivo, ficha, movimiento o None)."""
    a = rm.alineacion(e, ficha)
    if a is None:
        return e, base, m, ficha, None
    derecha = rm.mover(base, a)
    return rm.en_marco(e, a), derecha, rm.mover(m, a), fm.medir(derecha, tolerancia=ficha["tolerance"])[0], a


def _construir(sesion, plan, tol, nombre, faltas):
    e, base, _objetivo, ficha, _a = plan
    if e["kind"] == "revolve":
        return _giro(sesion, base, ficha, e["axis_point"], e["axis"], tol, nombre, faltas)
    return _prisma(sesion, base, ficha, e["direction"], tol, nombre, faltas)


def _ocultar(sesion, cuerpo_id):
    doc = sesion.doc
    ocultos = set(doc.propiedad("__navegador__", "ocultos", []))
    ocultos.add(cuerpo_id)
    doc.set_propiedad(["__navegador__"], "ocultos", sorted(ocultos))


def _para_medir(m):
    """Malla cerrada para cortar: una abierta se repara en una copia; se juzga siempre contra la original."""
    if m.es_cerrada():
        return m
    try:
        return ml.reparar(m)
    except geo.ErrorGeometria:
        return m


@herramienta("reconstruct_from_mesh", "malla", "Reconstruye una malla como pieza con timeline, sin IA (no convierte triángulos "
             "en caras como convert_mesh: mide la pieza y la vuelve a modelar). Elige revolución o pila de extrusiones, saca "
             "perfiles de líneas y arcos de los cortes, agrega agujeros, patrones de agujeros, empalmes y chaflanes, y hace "
             "vueltas de corrección: compara con la malla, suma lo que falta y corta lo que sobra, y corta sola si no mejora. "
             "Todos los pasos son normales y se editan como cualquier otro; el conjunto es UN paso de deshacer. La malla queda "
             "oculta. Devuelve desviación, % dentro de tolerancia, diferencia de volumen, caras, pasos creados, zonas fuera de "
             "tolerancia y lo que no se pudo recuperar. Si no alcanza la tolerancia igual deja la pieza y lo dice: "
             "tolerance_met=false. Superficies libres y roscas no se recuperan.", modifica=True)
def reconstruct_from_mesh(sesion, body: str, tolerance: float = 0.1, max_iterations: int = 3, name: str | None = None):
    """
    body: id o nombre del cuerpo de malla.
    tolerance: desviación máxima buscada en mm.
    max_iterations: tope de vueltas de corrección, de 0 a 10.
    name: nombre del cuerpo nuevo; vacío = «<malla> reconstruida».
    """
    _validar_tolerancia(tolerance)
    if not 0 <= max_iterations <= 10:
        raise error("INVALID_ARGUMENTS", f"max_iterations va de 0 a 10 (recibió {max_iterations}).")
    (cuerpo,) = _cuerpos(sesion, body, que="body")
    m = cuerpo.forma
    cm.exigir_malla(m)
    nombre = name.strip() if name and name.strip() else f"{sesion.nombre_cuerpo(cuerpo)} reconstruida"
    base = _para_medir(m)
    ficha = fm.medir(base, tolerancia=tolerance / 2 if fm.con_ruido(base) else None)[0]
    if ficha["unclassified_percent"] > _SIN_CLASIFICAR:
        ficha = fm.medir(base, tolerancia=tolerance / 2)[0]
    antes = len(sesion.doc.operaciones)
    intentos, mejor = rm.estrategia(ficha), None
    if not intentos:
        raise error("OPERATION_FAILED", "La malla no tiene planos ni ejes de donde partir: es una superficie libre.",
                    "Esto queda para RI-6; convert_mesh la pasa a sólido facetado.")
    errores = []
    limite = time.monotonic() + _PLAZO
    for i, e in enumerate(intentos):
        if mejor is not None and time.monotonic() > limite:
            continue
        faltas = []
        try:
            with sesion.transaccion():
                plan = _preparar(base, m, ficha, e)
                creado = _construir(sesion, plan, tolerance, nombre, faltas)
                juicio = _juez(sesion, creado, plan[2], tolerance)
                ultimo = i == len(intentos) - 1
                puntaje = (juicio["max_deviation"], i)
                if mejor is None or puntaje < mejor[0]:
                    mejor = (puntaje, e)
                if juicio["max_deviation"] <= tolerance or (ultimo and mejor[1] is e):
                    break
                raise _Probar
        except _Probar:
            continue
        except (ErrorAPI, geo.ErrorGeometria) as x:
            errores.append(f"{e['kind']}: {getattr(x, 'mensaje', x)}")
    else:
        if mejor is None:
            raise error("OPERATION_FAILED", "No se pudo reconstruir la malla. " + " · ".join(errores))
        faltas = []
        plan = _preparar(base, m, ficha, mejor[1])
        creado = _construir(sesion, plan, tolerance, nombre, faltas)
    try:
        with sesion.transaccion():
            vueltas = _corregir(sesion, plan[2], creado, tolerance, max_iterations, limite, faltas)
            if any(v["applied"] for v in vueltas):              # una corrección que pasa acá falló al reabrir en una pieza real
                _llamar(sesion, "recompute_all")
                if any(x.estado == "error" for x in sesion.doc.resultados):
                    raise _Probar
    except _Probar:
        vueltas = []
        faltas.append("Las correcciones fallaban al recalcular: se descartaron.")
    if plan[4] is not None:
        _llamar(sesion, "move_body", body=creado, rotate=[round(x, 6) for x in rm.angulos(plan[4]["R"])],
                translate=[round(float(x), 6) for x in plan[4]["t"]], pivot="origin")
    if sesion.nombre_cuerpo(sesion.cuerpo(creado)) != nombre:
        _llamar(sesion, "rename", target=creado, new_name=nombre, kind="body")
    _ocultar(sesion, cuerpo.id)
    final = sesion.cuerpo(creado)
    juicio = cm.comparar(final.forma, m, tolerancia=tolerance)
    pasos = [o.id for o in sesion.doc.operaciones[antes:]]
    logrado = juicio["max_deviation"] <= tolerance
    if not logrado:
        sesion.avisar(f"La pieza se aparta {juicio['max_deviation']:.3f} mm de la malla y la tolerancia es {tolerance:g} mm: "
                      "mirá zones_out_of_tolerance.")
    if ficha["unclassified_percent"] > 0.5:
        faltas.append(f"{ficha['unclassified_percent']:.1f} % del área no es una forma simple (superficie libre o rosca).")
    return dict(_informe(juicio), body=creado, name=nombre, strategy=_clase(sesion, pasos), tolerance=tolerance,
                tolerance_met=logrado, faces=len(sl.listar(final.forma, "cara")), steps_created=len(pasos), steps=pasos,
                valid=geo.es_valida(final.forma), mesh_hidden=cuerpo.id, iterations=vueltas, unrecovered=faltas,
                shapes=ficha["summary"], quality=ficha["quality"]["origin"])


def _clase(sesion, pasos):
    tipos = {o.TIPO for o in sesion.doc.operaciones if o.id in pasos}
    return "revolve" if any("revol" in t for t in tipos) else "prism"
