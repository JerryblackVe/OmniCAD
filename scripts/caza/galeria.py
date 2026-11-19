# -*- coding: utf-8 -*-
"""Caza con el Fusion 360 Gallery Dataset (Reconstruction), AG-20. Sin modelos y sin red (los datos ya están bajados).

Rehace boceto + extruir de cada diseño con la API de OmniCAD (`omnicad.api`) y compara volumen, área y caja envolvente
del resultado con los `properties` del JSON (Fusion, en cm). Los datos son de investigación: viven fuera del repo
(`~/datos/fusion_gallery/`, `OMNICAD_GALERIA`) y nunca se suben a git.

Uso, desde clon/ con el Python del venv (un diseño a la vez, cada uno en un proceso aparte; sin turno.py, que corta a los 900 s):
  ../scripts/caza/galeria.py correr [--n 500] [--semilla 1]     el informe sale en evidencias/galeria_<fecha>/
  ../scripts/caza/galeria.py uno <id_del_diseño>                un diseño, con el detalle (para reproducir un caso)
"""
import argparse
import json
import math
import os
import random
import re
import subprocess
import sys
from collections import defaultdict
from datetime import date
from pathlib import Path

AQUI = Path(__file__).resolve().parent
RAIZ = AQUI.parents[1]
DATOS = Path(os.environ.get("OMNICAD_GALERIA") or Path.home() / "datos" / "fusion_gallery") / "r1.0.1" / "reconstruction"
CURVAS_OK = ("SketchLine", "SketchArc", "SketchCircle")     # lo que el script sabe dibujar; el resto se cuenta aparte
TOL_REL = 1e-3          # volumen y área
TOL_CAJA = 0.02         # mm (más 1e-3 del tamaño)
PLAZO = 120             # s por diseño
CM = 10.0               # el dataset viene en cm


def _normal(msg):
    return re.sub(r"\d+(\.\d+)?", "#", str(msg))[:110]


def _vec(p):
    return [p["x"], p["y"], p["z"]]


def _mm(v):
    return [x * CM for x in v]


BASES = ((2, "XY", 1), (1, "XZ", -1), (0, "YZ", 1))      # eje de la normal, plano de origen de OmniCAD, signo de su normal


def base_de(e):
    """(plano de origen, desfase mm) donde cae el boceto de Fusion, o None si el plano está inclinado (la API no arma planos
    sueltos sin un vértice: el script solo cubre bocetos paralelos a un plano de origen)."""
    t = e["transform"]
    z, o = _vec(t["z_axis"]), _vec(t["origin"])
    for eje, plano, signo in BASES:
        if abs(abs(z[eje]) - 1) < 1e-6:
            return plano, o[eje] * CM * signo
    return None


def alcance(d):
    """None si el script puede rehacer el diseño; si no, el motivo (el diseño no cuenta como diferencia de OmniCAD)."""
    for e in d["entities"].values():
        if e["type"] == "Sketch":
            if e.get("curves") and base_de(e) is None:
                return "boceto en un plano inclinado"
            for c in e.get("curves", {}).values():
                if c["type"] not in CURVAS_OK:
                    return f"curva {c['type']}"
        elif e["type"] == "ExtrudeFeature":
            if e["extent_type"] not in ("OneSideFeatureExtentType", "SymmetricFeatureExtentType", "TwoSidesFeatureExtentType"):
                return f"extensión {e['extent_type']}"
    return None


def rasgos(d):
    """Qué usa el diseño: sirve para agrupar las diferencias por causa probable."""
    r = set()
    for e in d["entities"].values():
        if e["type"] == "Sketch":
            tipos = {c["type"] for c in e.get("curves", {}).values()}
            r |= {"arco"} if "SketchArc" in tipos else set()
            r |= {"sobre_cara"} if e["reference_plane"]["type"] != "ConstructionPlane" else set()
        elif e["type"] == "ExtrudeFeature":
            r.add({"NewBodyFeatureOperation": "nuevo", "JoinFeatureOperation": "unir", "CutFeatureOperation": "cortar",
                   "IntersectFeatureOperation": "intersecar"}[e["operation"]])
            r |= {"simetrico"} if e["extent_type"].startswith("Symm") else set()
            r |= {"dos_lados"} if e["extent_type"].startswith("TwoSides") else set()
            r |= {"inicio_desfasado"} if e["start_extent"]["type"] != "ProfilePlaneStartDefinition" else set()
            r |= {"conicidad"} if abs(e["extent_one"].get("taper_angle", {}).get("value", 0)) > 1e-9 else set()
            r |= {"varios_perfiles"} if len(e["profiles"]) > 1 else set()
    return sorted(r)


class Fallo(Exception):
    def __init__(self, etapa, msg):
        super().__init__(msg)
        self.etapa, self.msg = etapa, msg


def _llamar(api, s, etapa, nombre, **args):
    r = api.llamar(s, nombre, args)
    if not r["ok"]:
        raise Fallo(etapa, f"{nombre}: {r.get('mensaje') or r}")
    return r["result"]


def _a_local(marco, p):
    o, u, v = (marco[k] for k in ("origin", "u_axis", "v_axis"))
    dif = [p[i] - o[i] for i in range(3)]
    return [sum(dif[i] * u[i] for i in range(3)), sum(dif[i] * v[i] for i in range(3))]


def _dibujar(api, s, d, e, nombre, marco):
    """Dibuja las curvas del boceto de Fusion en el boceto de OmniCAD (pasando por el mundo: los dos marcos pueden diferir)."""
    t = e["transform"]
    o, xa, ya = _vec(t["origin"]), _vec(t["x_axis"]), _vec(t["y_axis"])

    def mundo(pid):
        p = e["points"][pid]
        return _mm([o[i] + p["x"] * xa[i] + p["y"] * ya[i] for i in range(3)])

    def loc(pid):
        return _a_local(marco, mundo(pid))

    for cid, c in e["curves"].items():
        if c.get("construction_geom"):
            continue
        if c["type"] == "SketchLine":
            (x1, y1), (x2, y2) = loc(c["start_point"]), loc(c["end_point"])
            if math.dist((x1, y1), (x2, y2)) > 1e-6:      # una línea sin largo no existe en OmniCAD ni se dibuja
                _llamar(api, s, "dibujar", "draw_line", sketch=nombre, start_x=x1, start_y=y1, end_x=x2, end_y=y2)
        elif c["type"] == "SketchCircle":
            x, y = loc(c["center_point"])
            _llamar(api, s, "dibujar", "draw_circle", sketch=nombre, center_x=x, center_y=y, radius=c["radius"] * CM)
        else:
            cen, a, b = e["points"][c["center_point"]], e["points"][c["start_point"]], e["points"][c["end_point"]]
            a0 = math.atan2(a["y"] - cen["y"], a["x"] - cen["x"])
            barrido = (math.atan2(b["y"] - cen["y"], b["x"] - cen["x"]) - a0) % (2 * math.pi)
            pm = {"x": cen["x"] + c["radius"] * math.cos(a0 + barrido / 2), "y": cen["y"] + c["radius"] * math.sin(a0 + barrido / 2),
                  "z": 0.0}
            e["points"]["_mid"] = pm
            (x1, y1), (xm, ym), (x2, y2) = loc(c["start_point"]), loc("_mid"), loc(c["end_point"])
            _llamar(api, s, "dibujar", "draw_arc", sketch=nombre, start_x=x1, start_y=y1, mid_x=xm, mid_y=ym, end_x=x2, end_y=y2)


def _perfil(api, s, e, uid_perfil, nombre, marco):
    """Índice del perfil de OmniCAD que corresponde al perfil de Fusion: mismo área y, entre iguales, el centroide más cerca."""
    p = e["profiles"][uid_perfil]["properties"]
    area = p["area"] * CM * CM
    t, c = e["transform"], p["centroid"]        # el centroide del JSON está en coordenadas del boceto, no del mundo
    o, xa, ya = _vec(t["origin"]), _vec(t["x_axis"]), _vec(t["y_axis"])
    cen = _a_local(marco, _mm([o[i] + c["x"] * xa[i] + c["y"] * ya[i] for i in range(3)]))
    perfiles = _llamar(api, s, "perfil", "get_sketch", sketch=nombre)["profiles"]
    cand = [q for q in perfiles if abs(q["area"] - area) <= TOL_REL * max(area, 1e-9) + 1e-6]
    if not cand:
        raise Fallo("perfil", f"sin perfil de área {area:.1f} mm2: OmniCAD tiene {len(perfiles)} perfiles de áreas "
                    f"{sorted(round(q['area']) for q in perfiles)[:6]}")
    return min(cand, key=lambda q: math.dist(q["centroid"], cen))["index"]


def rehacer(d):
    """Rehace el diseño; devuelve (volumen mm3, área mm2, caja mn, mx) o levanta Fallo."""
    sys.path.insert(0, str(RAIZ / "clon"))
    from omnicad import api
    s = api.Sesion()
    marcos = {}
    for n, it in enumerate(d["timeline"]):
        uid = it["entity"]
        e = d["entities"][uid]
        if e["type"] == "Sketch":
            if not e.get("curves"):
                continue
            base, desfase = base_de(e)
            plano = base if abs(desfase) < 1e-9 else _llamar(api, s, "plano", "create_construction_plane", plane=base,
                                                            offset=desfase, name=f"P{n}")["plane"]["id"]
            info = _llamar(api, s, "boceto", "create_sketch", plane=plano, name=f"S{n}")
            marcos[uid] = (f"S{n}", info["plane_frame"])
            _dibujar(api, s, d, e, f"S{n}", info["plane_frame"])
        elif e["type"] == "ExtrudeFeature":
            perfiles = []
            for pr in e["profiles"]:
                if pr["sketch"] not in marcos:
                    raise Fallo("extruir", "el perfil es de un boceto sin curvas o fuera del alcance")
                nombre, marco = marcos[pr["sketch"]]
                perfiles.append({"sketch": nombre, "profile": _perfil(api, s, d["entities"][pr["sketch"]], pr["profile"], nombre, marco)})
            nombre, marco = marcos[e["profiles"][0]["sketch"]]
            za = _vec(d["entities"][e["profiles"][0]["sketch"]]["transform"]["z_axis"])
            signo = 1 if sum(za[i] * marco["normal"][i] for i in range(3)) >= 0 else -1    # la normal de OmniCAD, ¿mira igual?
            uno = e["extent_one"]
            dist = uno["distance"]["value"] * CM * signo
            args = dict(profiles=perfiles, operation={"NewBodyFeatureOperation": "new_body", "JoinFeatureOperation": "join",
                                                      "CutFeatureOperation": "cut", "IntersectFeatureOperation": "intersect"}[e["operation"]],
                        taper_angle=math.degrees(uno.get("taper_angle", {}).get("value", 0.0)))
            if e["extent_type"].startswith("Symm"):
                args.update(direction="symmetric", distance=abs(dist), symmetric_measure="total" if uno.get("is_full_length") else "half")
            elif e["extent_type"].startswith("TwoSides") and abs(e["extent_two"]["distance"]["value"]) > 1e-9:    # lado 2 en 0 = un solo lado
                dos = e["extent_two"]["distance"]["value"] * CM * signo
                args.update(direction="two_sides", distance=abs(dist), distance2=abs(dos), reverse=dist < 0)
            else:
                args.update(distance=abs(dist), reverse=dist < 0)
            if e["start_extent"]["type"] != "ProfilePlaneStartDefinition":
                args.update(start="offset", start_offset=e["start_extent"].get("offset", {}).get("value", 0.0) * CM * signo)
            _llamar(api, s, "extruir", "extrude", **args)
    r = _llamar(api, s, "medir", "get_physical_properties")["total"]
    return r["volume"], r["area"], r["bounding_box"]


def comparar(d, res):
    p = d["properties"]
    vol, area, caja = p["volume"] * CM ** 3, p["area"] * CM ** 2, p["bounding_box"]
    mn, mx = _mm(_vec(caja["min_point"])), _mm(_vec(caja["max_point"]))
    dif = {}
    if abs(res[0] - vol) > TOL_REL * max(vol, 1e-9):
        dif["volumen"] = (round(res[0], 2), round(vol, 2))
    if abs(res[1] - area) > TOL_REL * max(area, 1e-9):
        dif["area"] = (round(res[1], 2), round(area, 2))
    if res[2] is None or any(abs(a - b) > TOL_CAJA + 1e-3 * (mx[i % 3] - mn[i % 3]) for i, (a, b) in
                             enumerate(zip(list(res[2]["min"]) + list(res[2]["max"]), mn + mx, strict=True))):
        dif["caja"] = (res[2] and [round(x, 2) for x in list(res[2]["min"]) + list(res[2]["max"])], [round(x, 2) for x in mn + mx])
    return dif


def uno(ident):
    d = json.load(open(DATOS / f"{ident}.json"))
    sal = {"id": ident, "rasgos": rasgos(d)}
    motivo = alcance(d)
    if motivo:
        sal["estado"], sal["motivo"] = "fuera_de_alcance", motivo
        return sal
    try:
        res = rehacer(d)
    except Fallo as f:
        sal.update(estado="error", etapa=f.etapa, causa=_normal(f.msg), detalle=f.msg[:300])
        return sal
    except Exception as f:                       # una excepción que escapa de la API es un hallazgo, no del script
        sal.update(estado="error", etapa="excepcion", causa=_normal(f"{type(f).__name__}: {f}"), detalle=repr(f)[:300])
        return sal
    dif = comparar(d, res)
    sal.update(estado="difiere" if dif else "ok", dif={k: v for k, v in dif.items()})
    return sal


def correr(args):
    ids = sorted(p.stem for p in DATOS.glob("*_0000.json"))
    random.Random(args.semilla).shuffle(ids)
    carpeta = RAIZ / "evidencias" / f"galeria_{date.today().isoformat()}"
    carpeta.mkdir(parents=True, exist_ok=True)
    resultados, fuera = [], 0
    for ident in ids:
        if len([r for r in resultados if r["estado"] != "fuera_de_alcance"]) >= args.n:
            break
        d = json.load(open(DATOS / f"{ident}.json"))
        if alcance(d):
            fuera += 1
            continue
        try:
            sal = subprocess.run([sys.executable, __file__, "uno", ident, "--json"], capture_output=True, text=True,
                                 timeout=PLAZO, env={**os.environ, "QT_QPA_PLATFORM": "offscreen"})
            r = json.loads(sal.stdout.strip().splitlines()[-1]) if sal.returncode == 0 and sal.stdout.strip() else {
                "id": ident, "rasgos": rasgos(d), "estado": "error", "etapa": "proceso",
                "causa": _normal(sal.stderr.strip().splitlines()[-1] if sal.stderr.strip() else f"salida {sal.returncode}"), "detalle": sal.stderr[-300:]}
        except subprocess.TimeoutExpired:
            r = {"id": ident, "rasgos": rasgos(d), "estado": "error", "etapa": "proceso", "causa": f"más de {PLAZO} s", "detalle": ""}
        resultados.append(r)
        print(f"[{len(resultados):3d}] {ident} {r['estado']} {r.get('causa', '') or r.get('dif', '')}", flush=True)
    informe(carpeta, resultados, fuera)


def informe(carpeta, resultados, fuera):
    (carpeta / "resultados.json").write_text(json.dumps(resultados, ensure_ascii=False, indent=1), encoding="utf-8")
    n = len(resultados)
    cuenta = defaultdict(int)
    for r in resultados:
        cuenta[r["estado"]] += 1
    causas = defaultdict(list)
    for r in resultados:
        if r["estado"] == "error":
            causas[f"error · {r['etapa']} · {r['causa']}"].append(r["id"])
        elif r["estado"] == "difiere":
            causas[f"diferencia en {'+'.join(sorted(r['dif']))} · {' '.join(r['rasgos'])}"].append(r["id"])
    lineas = [f"# Caza con Fusion 360 Gallery (Reconstruction) · {date.today().isoformat()}", "",
              f"{n} diseños rehechos con la API (otros {fuera} quedaron fuera del alcance del script: splines, elipses o extensiones raras). "
              f"OK {cuenta['ok']} · difieren {cuenta['difiere']} · error {cuenta['error']}.", "",
              "Tolerancia: 0,1 % en volumen y área; caja envolvente 0,02 mm + 0,1 % del tamaño. Datos del JSON en cm → mm.", ""]
    for causa, ids in sorted(causas.items(), key=lambda kv: -len(kv[1])):
        lineas += [f"## {len(ids)} · {causa}", "ids: " + ", ".join(ids[:15]) + (" …" if len(ids) > 15 else ""), ""]
    (carpeta / "informe.md").write_text("\n".join(lineas), encoding="utf-8")
    print("\n".join(lineas[:6]))


def principal():
    ap = argparse.ArgumentParser(description=__doc__)
    sub = ap.add_subparsers(dest="modo", required=True)
    c = sub.add_parser("correr")
    c.add_argument("--n", type=int, default=500)
    c.add_argument("--semilla", type=int, default=1)
    u = sub.add_parser("uno")
    u.add_argument("ident")
    u.add_argument("--json", action="store_true")
    a = ap.parse_args()
    if a.modo == "uno":
        r = uno(a.ident)
        print(json.dumps(r, ensure_ascii=False) if a.json else json.dumps(r, ensure_ascii=False, indent=1))
    else:
        correr(a)


if __name__ == "__main__":
    principal()
