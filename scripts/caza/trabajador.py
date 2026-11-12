# -*- coding: utf-8 -*-
"""Proceso aislado de la caza: atiende pedidos JSON (uno por línea) y corre los casos sin modelos ni red.

Lo lanza `cazar.py` con la carpeta temporal en las variables de entorno. Antes de cada llamada anota el paso en stderr
(la bitácora): si el proceso se cae o se cuelga, `cazar.py` rearma la receta desde ahí."""
import ctypes
import faulthandler
import json
import os
import random
import re
import sys
import tempfile
import time
import traceback
import zipfile
from pathlib import Path

AQUI = Path(__file__).resolve().parent
sys.path.insert(0, str(AQUI))
sys.path.insert(0, os.environ.get("OMNICAD_CODIGO") or str(AQUI.parents[1] / "clon"))

import generador as gen  # noqa: E402
import jueces as j  # noqa: E402
from omnicad import api  # noqa: E402
from omnicad.api import registro  # noqa: E402

PRESUPUESTO = 25.0          # s por caso: pasado esto, los jueces que rehacen la pieza se saltean
HERRAMIENTAS = {h["nombre"]: h for h in api.catalogo()}
CORPUS = (AQUI.parents[1] / "clon" / "tests" / "corpus_caza").as_posix()
ULTIMA = [""]               # última línea propia de la pila del último error suelto


def _traducir_con_pila(original):
    def traducir(e):
        propias = [f for f in traceback.extract_tb(e.__traceback__) if "omnicad" in f.filename and "registro.py" not in f.filename]
        ULTIMA[0] = f"{Path(propias[-1].filename).name}:{propias[-1].lineno}" if propias else ""
        return original(e)
    return traducir


registro.traducir = _traducir_con_pila(registro.traducir)


def preparar_proceso():
    """Sin red, sin cuadros de error de Windows y con el rastro nativo en la bitácora."""
    import socket

    def sin_red(*_a, **_k):
        raise OSError("la caza no abre red")
    socket.socket.connect = sin_red
    faulthandler.enable()
    j.vigilar_memoria()
    if os.name == "nt":
        ctypes.windll.kernel32.SetErrorMode(0x8003)     # sin diálogos: un cierre brusco sale directo


def resolver(args, carpeta):
    """Las recetas guardan {TMP} (la carpeta del caso) y {CORPUS} (archivos alterados de la regresión)."""
    return json.loads(json.dumps(args).replace("{TMP}", Path(carpeta).as_posix()).replace("{CORPUS}", CORPUS))


def llamar(s, tool, args, carpeta):
    """Llamada con los {TMP} de la receta resueltos y anotada en la bitácora."""
    print("PASO " + json.dumps({"tool": tool, "args": args}, ensure_ascii=False), file=sys.stderr, flush=True)
    return api.llamar(s, tool, resolver(args, carpeta))


def firma(falla):
    return f"{falla['juez']}|{falla.get('op', '')}|{falla['kind']}"


def _firma_interna(f, tool):
    if f["kind"] == "INTERNAL_ERROR" and ULTIMA[0]:
        f["kind"] = f"INTERNAL_ERROR@{ULTIMA[0]}"
    f["op"] = tool
    return f


def juzgar(s, tool, args, receta, antes, f_previa, carpeta, pesado, todos, t0, invalido=None, exito=False):
    """Los jueces, del más grave al más caro, sobre un paso que dio ok. Devuelve (fallo, foto, defectos).
    Sin `todos`, los que rehacen la pieza corren en uno de cada tres pasos: la `rapida` prueba el doble de cadenas."""
    f = j.foto(api, s)
    falla = j.juez_numeros({n: c for n, c in f.items() if c != f_previa.get(n)})      # lo heredado ya se juzgó
    if falla:
        return falla, f, antes
    cubos = {c["type"] for c in (api.llamar(s, "find_faces", {}).get("result") or {}).get("faces") or []}
    d = j.defectos(api, s, pesado or not cubos & {"bspline", "bezier", "other"}, solidos=exito)
    falla = j.juez_geometria({} if exito else antes, d) or j.juez_esperado(tool, args, f_previa, f)
    # Sobre una pieza ya rota, los jueces que la rehacen culpan al paso que venga después.
    rota = any(n for defectos in d.values() for n in defectos.values())
    if falla or invalido or rota or not (todos or len(receta) % 3 == 0):
        return falla, f, d
    rehacer = lambda: rehacer_receta(receta[:-1], carpeta)  # noqa: E731
    jueces = (lambda: j.juez_recalcular(api, s, f), lambda: j.juez_guardar(api, s, f, carpeta),
              lambda: j.juez_exportar(api, s, f, carpeta), lambda: j.juez_editar(api, s, f),
              lambda: j.juez_mover(api, rehacer, tool, args, f))
    if HERRAMIENTAS[tool]["transaccion"]:                # sin transacción no hay paso propio que deshacer
        jueces = (lambda: j.juez_deshacer(api, s, f_previa, f), *jueces)
    if tool == "boolean_operation":
        jueces += (lambda: j.juez_identidad(api, rehacer, args, f_previa, f),)
    for juez in jueces:
        if time.monotonic() - t0 > PRESUPUESTO:
            break
        falla = juez()
        if falla:
            return falla, f, d
    return None, f, d


def rehacer_receta(pasos, carpeta):
    s = api.Sesion()
    for p in pasos:
        j.refrescar(api, s)
        api.llamar(s, p["tool"], resolver(p["args"], carpeta))
    return s


def correr(pasos, carpeta, pesado=False, todos=True, ignorar=()):
    """Corre los pasos (un iterable que puede depender de la sesión) y se detiene en el primer fallo de un juez,
    salvo los de `ignorar`: lo que ya salió muchas veces no gasta la cadena."""
    t0 = time.monotonic()
    s = api.Sesion()
    ignorar = {*ignorar, *j.ADMITIDOS}
    receta, avance = [], []
    defectos, previa = {}, {}
    pico = memoria_pico()
    for paso in pasos(s):
        tool, args = paso["tool"], paso["args"]
        j.refrescar(api, s)
        receta_antes = json.dumps((api.llamar(s, "get_recipe", {}).get("result") or {}), default=str)
        t = time.monotonic()
        r = llamar(s, tool, args, carpeta)
        avance.append({"tool": tool, "ok": bool(r.get("ok")), "kind": r.get("error_kind"), "clase": paso.get("clase"),
                       "seg": round(time.monotonic() - t, 3)})
        invalido = paso.get("invalido")
        falla = j.juez_memoria(tool, pico, memoria_pico()) or j.juez_contrato(r, invalido, paso.get("exito", False))
        receta.append({k: v for k, v in paso.items() if k != "clase"})
        if falla and firma(_firma_interna(falla, tool)) not in ignorar:
            return {"fallo": falla, "receta": receta, "avance": avance}
        if not r.get("ok"):
            receta.pop()
            continue
        if not paso.get("exito") and json.dumps((api.llamar(s, "get_recipe", {}).get("result") or {}), default=str) == receta_antes:
            continue                                            # no cambió el documento: no hay nada que juzgar
        falla, previa, defectos = juzgar(s, tool, args, receta, defectos, previa, carpeta, pesado, todos, t0,
                                       invalido, paso.get("exito", False))
        if falla and firma(_firma_interna(falla, tool)) not in ignorar:
            return {"fallo": falla, "receta": receta, "avance": avance}
    return {"fallo": None, "receta": receta, "avance": avance}


def pasos_cadena(ped, rng):
    """Generador: primero la pieza semilla, después el plan del coordinador, con argumentos medidos en la pieza."""
    def pasos(s):
        real = ped["pieza"] in gen.CADENAS_REALES
        pieza = gen.CADENAS_REALES[ped["pieza"]] if real else gen.PIEZAS[ped["pieza"]]
        for tool, args in pieza(rng):
            yield {"tool": tool, "args": args, **({"exito": True} if real else {})}
        for tool, clase in ped["plan"]:
            ctx = gen.Contexto(s, api.llamar)
            args = gen.llenar(HERRAMIENTAS[tool], ctx, rng, clase)
            if args is None:
                ped.setdefault("sin_contexto", []).append(tool)
                continue
            yield {"tool": tool, "args": args, "clase": clase}
    return pasos


def cadena(ped):
    with tempfile.TemporaryDirectory(prefix="caza_") as carpeta:
        res = correr(pasos_cadena(ped, random.Random(ped["semilla"])), carpeta, ped.get("pesado", False),
                     ped.get("pesado", False), ped.get("ignorar", ()))
    res["sin_contexto"] = ped.get("sin_contexto", [])
    return res


def repetir(ped):
    with tempfile.TemporaryDirectory(prefix="caza_") as carpeta:
        return correr(lambda _s: iter(ped["pasos"]), carpeta, ped.get("pesado", False), ignorar=ped.get("ignorar", ()))


def valores(prop, nombre):
    """(clase, valor, invalido) de borde e inválidos según el esquema, sin salir nunca de la carpeta temporal."""
    tip = gen.tipos(prop)
    positivo = bool(re.search(r"positiv|mayor que (0|cero)|más de 0", prop.get("description", "")))
    if "enum" in prop:
        salida = [("enum_malo", "no_existe", False)]
    elif "string" in tip and "number" not in tip and (nombre in ("path", "source_path") or gen.RUTA.search(prop.get("description", ""))):
        return [("ruta_vacia", "", False), ("ruta_falsa", "{TMP}/no_existe.xyz", False), ("ruta_tipo", 7, False)]
    else:
        salida = []
        if tip & {"number", "integer"}:
            salida += [("0", 0, positivo), ("neg", -1, positivo), ("1e-6", 1e-6, False), ("1e6", 10**6, False),
                       ("nan", float("nan"), False), ("inf", float("inf"), False)]
        if "string" in tip:
            salida += [("vacio", "", False), ("largo", "x" * 5000, False), ("eñe", "Ñandú ñ", False)]
        if "array" in tip:
            salida += [("lista_vacia", [], False), ("lista_nula", [None], False)]
        if "object" in tip:
            salida += [("objeto_vacio", {}, False)]
    if "null" not in tip:
        salida.append(("nulo", None, False))
    return [*salida, ("tipo_malo", {"x": 1} if "object" not in tip else 7, False)]


def contratos(ped):
    """Capa A: una herramienta con cada parámetro en valores de borde e inválidos, desde la variante `desde`."""
    h = HERRAMIENTAS[ped["tool"]]
    rng = random.Random(ped["semilla"])
    props = h["esquema"]["properties"]
    variantes = [(None, None, False)] + [(k, c, (v, inv)) for k, p in props.items() for c, v, inv in valores(p, k)]
    fallos, avance = [], []
    pieza = [{"tool": t, "args": a} for t, a in gen.PIEZAS["contrato"](rng)]
    t0, i = time.monotonic(), ped["desde"]
    with tempfile.TemporaryDirectory(prefix="caza_") as carpeta:
        s = rehacer_receta(pieza, carpeta)
        normal = gen.llenar(h, gen.Contexto(s, api.llamar), rng, "m") or {}
        while i < len(variantes) and (time.monotonic() - t0 < ped["segundos"] or i == ped["desde"]):
            param, clase, dato = variantes[i]
            i += 1
            args = dict(normal)
            if param:
                args[param] = dato[0]
            invalido = param if dato and dato[1] else None
            r = llamar(s, h["nombre"], args, carpeta)
            avance.append({"tool": h["nombre"], "ok": bool(r.get("ok")), "kind": r.get("error_kind"), "clase": None})
            paso = {"tool": h["nombre"], "args": args, **({"invalido": invalido} if invalido else {})}
            falla = j.juez_memoria(h["nombre"]) or j.juez_contrato(r, invalido)
            if r.get("ok") and h["modifica"]:
                falla = falla or j.juez_numeros(j.foto(api, s))
                s = rehacer_receta(pieza, carpeta)
            if falla:
                falla = _firma_interna(falla, h["nombre"])
                falla["kind"] = f"{falla['kind']}:{param}" if param and falla["kind"] == "acepta_invalido" else falla["kind"]
                fallos.append({"fallo": falla, "receta": [*pieza, paso]})
    return {"fallos": fallos, "avance": avance, "hechos": i if i < len(variantes) else 0}


MUESTRAS = {}               # extensión → bytes del archivo sano, una vez por proceso


def muestra(ext):
    """Archivo sano de cada formato, armado con la propia app (el .f3d es solo el contenedor: la app no escribe .f3d)."""
    if ext not in MUESTRAS:
        with tempfile.TemporaryDirectory(prefix="caza_") as carpeta:
            ruta = Path(carpeta) / f"sana{ext}"
            s = rehacer_receta([{"tool": t, "args": a} for t, a in gen.PIEZAS["extruido"](random.Random(0))], carpeta)
            if ext == ".omnicad":
                api.llamar(s, "save_document", {"path": str(ruta)})
            elif ext in (".dxf", ".svg"):
                api.llamar(s, "export_sketch", {"path": str(ruta), "sketch": "Boceto1"})
            elif ext == ".f3d":
                with zipfile.ZipFile(ruta, "w") as z:
                    z.writestr("Manifest.dat", "omnicad caza")
                    z.writestr("FusionAssetName[Active]/Breps.BlobParts/BREP.smbh", b"\x00" * 256)
            else:
                api.llamar(s, "export", {"path": str(ruta)})
            MUESTRAS[ext] = ruta.read_bytes()
    return MUESTRAS[ext]


def mutar(datos, rng):
    """Bytes alterados: voltear, cortar, poner ceros, insertar basura o repetir un bloque."""
    b = bytearray(datos)
    i = rng.randrange(max(len(b), 1))
    largo = rng.choice((1, 4, 64, 1024))
    tipo = rng.choice(("voltear", "cortar", "ceros", "insertar", "repetir"))
    if tipo == "voltear":
        for _ in range(rng.choice((1, 8, 64))):
            b[rng.randrange(len(b))] ^= 1 << rng.randrange(8)
    elif tipo == "cortar":
        del b[i:]
    elif tipo == "ceros":
        b[i:i + largo] = bytes(len(b[i:i + largo]))
    elif tipo == "insertar":
        b[i:i] = rng.randbytes(largo)
    else:
        b[i:i] = b[i:i + largo] * 50
    return bytes(b)


def archivo(ped):
    """Capa C: abre un archivo alterado. Queda en disco hasta que termina: si tira el proceso, es la evidencia."""
    ext, rng = ped["ext"], random.Random(ped["semilla"])
    ruta = Path(ped["carpeta"]) / f"{ped['ext'][1:]}_{abs(hash(ped['semilla'])) % 10**8}{ext}"
    ruta.parent.mkdir(parents=True, exist_ok=True)
    ruta.write_bytes(mutar(muestra(ext), rng))
    args = {"path": ruta.as_posix()}
    tool = {".dxf": "insert_dxf", ".svg": "insert_svg", ".f3d": "inspect_f3d"}.get(ext, "open_document")
    with tempfile.TemporaryDirectory(prefix="caza_") as carpeta:
        s = api.Sesion()
        r = llamar(s, tool, args, carpeta)
        falla = j.juez_memoria(tool) or j.juez_contrato(r) or (j.juez_numeros(j.foto(api, s)) if r.get("ok") else None)
    avance = [{"tool": tool, "ok": bool(r.get("ok")), "kind": r.get("error_kind"), "clase": None}]
    if not falla:
        ruta.unlink()
        return {"fallo": None, "avance": avance, "receta": []}
    return {"fallo": _firma_interna(falla, tool), "avance": avance,
            "receta": [{"tool": tool, "args": args}]}


def memoria_pico():
    """MB máximos que usó este proceso."""
    if os.name != "nt":
        import resource
        return resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024

    class Cuenta(ctypes.Structure):
        _fields_ = [("cb", ctypes.c_ulong), ("fallos", ctypes.c_ulong), ("pico", ctypes.c_size_t), ("resto", ctypes.c_size_t * 7)]
    c = Cuenta()
    c.cb = ctypes.sizeof(c)
    ctypes.windll.psapi.GetProcessMemoryInfo(ctypes.c_void_p(-1), ctypes.byref(c), c.cb)
    return c.pico / 2**20


def medir(ped):
    """Capa E: tiempo y memoria de una receta fija, corrida tres veces (vale la mediana)."""
    receta = gen.RECETAS_FIJAS[ped["receta"]]
    tiempos = []
    with tempfile.TemporaryDirectory(prefix="caza_") as carpeta:
        for _ in range(3):
            t = time.perf_counter()
            rehacer_receta(receta, carpeta)
            tiempos.append(time.perf_counter() - t)
    return {"seg": sorted(tiempos)[1], "mb": memoria_pico()}


def catalogo(_ped):
    return {"herramientas": [{"nombre": h["nombre"], "modifica": h["modifica"], "descripcion": h["descripcion"],
                              "nucleo": gen.es_nucleo(h)}
                             for h in HERRAMIENTAS.values() if h["nombre"] not in gen.EXCLUIDAS],
            "excluidas": gen.EXCLUIDAS, "fuera_de_cadena": sorted(gen.FUERA_DE_CADENA), "recetas_fijas": sorted(gen.RECETAS_FIJAS)}


def imagen(ped):
    """Render del caso, para el informe."""
    with tempfile.TemporaryDirectory(prefix="caza_") as carpeta:
        s = rehacer_receta(ped["pasos"], carpeta)
        r = api.llamar(s, "get_viewport_image", {"view": "iso"})
    if r.get("ok"):
        Path(ped["ruta"]).write_bytes(r["result"]["image"].png)
    return {"ok": bool(r.get("ok"))}


ATENDER = {"cadena": cadena, "repetir": repetir, "catalogo": catalogo, "imagen": imagen, "contratos": contratos,
           "archivo": archivo, "medir": medir}


def principal():
    salida = os.fdopen(os.dup(1), "w", encoding="utf-8", buffering=1)
    os.dup2(2, 1)                 # lo que imprima el núcleo no ensucia el canal de respuestas
    preparar_proceso()
    for linea in sys.stdin:
        ped = json.loads(linea)
        try:
            res = ATENDER[ped["tipo"]](ped)
        except Exception as e:  # noqa: BLE001 — una excepción del cazador no es un hallazgo de la app
            res = {"error_cazador": "".join(traceback.format_exception(e))[-1500:]}
        salida.write(json.dumps(res, ensure_ascii=False, default=str) + "\n")


if __name__ == "__main__":
    principal()
